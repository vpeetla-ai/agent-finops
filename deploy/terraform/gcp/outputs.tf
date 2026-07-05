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

output "agentfinops_api_key" {
  description = "The real generated AGENTFINOPS_API_KEY (send as X-API-Key) when var.agentfinops_api_key isn't set explicitly."
  value       = random_password.agentfinops_api_key.result
  sensitive   = true
}
