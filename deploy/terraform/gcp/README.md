# GCP deploy — Cloud Run + Cloud SQL

A real, alternative deploy path to the Render PaaS in the root `render.yaml` — Cloud Run
(scale-to-zero) + Cloud SQL (Postgres, smallest tier, no HA). See
[docs/adr/0002-paas-vs-iac-deploy-tradeoffs.md](../../../docs/adr/0002-paas-vs-iac-deploy-tradeoffs.md)
for when this earns its complexity over the PaaS path.

**Cost while running:** Cloud Run itself is ≈$0 at low/demo traffic (pay-per-request,
scale-to-zero). Cloud SQL's `db-f1-micro` tier is the real fixed cost, roughly $7–10/month.
**Operating model: stand up, verify, tear down** — `terraform destroy` (or at minimum stop the
Cloud SQL instance) when not actively verifying, not left running 24/7.

## Prerequisites

- `gcloud auth application-default login` (run this yourself — this repo never handles your
  raw credentials)
- A GCP project with billing enabled; `gcloud config set project <PROJECT_ID>`
- `terraform`, `gcloud`, `docker` installed locally

## Deploy

```bash
# 1. Enable APIs + create the Artifact Registry repo (first apply only needs this much)
cd deploy/terraform/gcp
terraform init
terraform apply -target=google_project_service.artifactregistry -target=google_artifact_registry_repository.agent_finops

# 2. Build and push the image
gcloud auth configure-docker <REGION>-docker.pkg.dev
docker build -t <REGION>-docker.pkg.dev/<PROJECT_ID>/agent-finops/agent-finops:latest ../../..
docker push <REGION>-docker.pkg.dev/<PROJECT_ID>/agent-finops/agent-finops:latest

# 3. Apply everything else (Cloud SQL, Secret Manager, service account, Cloud Run)
terraform apply -var="project_id=<PROJECT_ID>" -var="region=<REGION>"
```

## Verify

```bash
SERVICE_URL=$(terraform output -raw service_url)
curl -s "$SERVICE_URL/health"
```

## Tear down

```bash
terraform destroy -var="project_id=<PROJECT_ID>" -var="region=<REGION>"
```
