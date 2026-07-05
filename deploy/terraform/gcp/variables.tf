variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run, Cloud SQL, and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "image_tag" {
  description = "Container image tag to deploy (pushed to Artifact Registry before apply)."
  type        = string
  default     = "latest"
}

variable "agentfinops_api_key" {
  description = "Value for AGENTFINOPS_API_KEY. Leave empty to run the service open (dev/demo default)."
  type        = string
  default     = ""
  sensitive   = true
}
