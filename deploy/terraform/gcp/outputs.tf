output "service_url" {
  description = "Live URL of the deployed agent-finops Cloud Run service."
  value       = google_cloud_run_v2_service.agent_finops.uri
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name (project:region:instance)."
  value       = google_sql_database_instance.agent_finops.connection_name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository to push the container image to before apply."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_finops.repository_id}"
}
