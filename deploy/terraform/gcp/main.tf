# Real, running AWS/GCP infra — a genuine alternative to the Render/Vercel PaaS
# path every other repo in this org uses, not a portfolio-only exercise. See
# docs/adr/0002-paas-vs-iac-deploy-tradeoffs.md for when each earns its
# complexity. Lowest-cost configuration on purpose: Cloud Run scale-to-zero
# (min_instance_count = 0) and Cloud SQL's smallest shared-core tier with no
# HA replica. Intended to be stood up, verified, and torn down per session
# (terraform apply -> verify -> terraform destroy), not left running.

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Enabled APIs -----------------------------------------------------------

resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "sqladmin" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# --- Artifact Registry --------------------------------------------------

resource "google_artifact_registry_repository" "agent_finops" {
  repository_id = "agent-finops"
  location      = var.region
  format        = "DOCKER"
  depends_on    = [google_project_service.artifactregistry]
}

# --- Cloud SQL (Postgres, smallest tier, no HA) --------------------------

resource "google_sql_database_instance" "agent_finops" {
  name             = "agent-finops-db"
  database_version = "POSTGRES_15"
  region           = var.region
  depends_on       = [google_project_service.sqladmin]

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL" # no HA replica -- lowest cost, matches this phase's operating model
    disk_size         = 10      # smallest billable size, GB
    disk_autoresize   = false
  }

  deletion_protection = false # this instance is meant to be torn down between sessions
}

resource "google_sql_database" "agent_finops" {
  name     = "agent_finops"
  instance = google_sql_database_instance.agent_finops.name
}

resource "random_password" "db_password" {
  length  = 24
  special = false # keep the URL-safe for a libpq connection string
}

resource "google_sql_user" "agent_finops" {
  name     = "agent_finops"
  instance = google_sql_database_instance.agent_finops.name
  password = random_password.db_password.result
}

# --- Secret Manager -------------------------------------------------------

resource "google_secret_manager_secret" "database_url" {
  secret_id  = "agent-finops-database-url"
  depends_on = [google_project_service.secretmanager]
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql://${google_sql_user.agent_finops.name}:${random_password.db_password.result}@/${google_sql_database.agent_finops.name}?host=/cloudsql/${google_sql_database_instance.agent_finops.connection_name}"
}

resource "google_secret_manager_secret" "api_key" {
  secret_id  = "agent-finops-api-key"
  depends_on = [google_project_service.secretmanager]
  replication {
    auto {}
  }
}

resource "random_password" "agentfinops_api_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret_version" "api_key" {
  secret = google_secret_manager_secret.api_key.id
  # A real generated key by default -- this service is invokable by allUsers
  # at the IAM layer (see google_cloud_run_v2_service_iam_member.public_invoker
  # below), so AGENTFINOPS_API_KEY is the only real gate; a placeholder
  # string here would be a guessable "password."
  secret_data = var.agentfinops_api_key != "" ? var.agentfinops_api_key : random_password.agentfinops_api_key.result
}

# --- Service account (least privilege) ------------------------------------

resource "google_service_account" "agent_finops_run" {
  account_id   = "agent-finops-run"
  display_name = "agent-finops Cloud Run runtime identity"
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.agent_finops_run.email}"
}

resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_finops_run.email}"
}

resource "google_secret_manager_secret_iam_member" "api_key_access" {
  secret_id = google_secret_manager_secret.api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_finops_run.email}"
}

# --- Cloud Run (scale-to-zero) ---------------------------------------------

resource "google_cloud_run_v2_service" "agent_finops" {
  name                = "agent-finops"
  location            = var.region
  deletion_protection = false # this service is meant to be torn down between sessions
  depends_on          = [google_project_service.run]

  template {
    service_account = google_service_account.agent_finops_run.email

    scaling {
      min_instance_count = 0 # scale-to-zero -- near-$0 at low/demo traffic
      max_instance_count = 2
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_finops.repository_id}/agent-finops:${var.image_tag}"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "AGENTFINOPS_DB_BACKEND"
        value = "postgres"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "AGENTFINOPS_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_key.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.agent_finops.connection_name]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.agent_finops.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers" # governed by AGENTFINOPS_API_KEY at the application layer, not IAM
}
