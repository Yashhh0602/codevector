variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "codevector"
}

variable "container_port" {
  description = "Port the FastAPI app listens on inside the container"
  type        = number
  default     = 8000
}

variable "db_name" {
  description = "Postgres database name"
  type        = string
  default     = "codevector"
}

variable "db_username" {
  description = "Postgres master username"
  type        = string
  default     = "codevector_admin"
}

variable "db_password" {
  description = "Postgres master password — set this in terraform.tfvars, never commit it"
  type        = string
  sensitive   = true
}

variable "ecr_image_uri" {
  description = "Full ECR image URI (repo:tag) to deploy — set after your first ECR push"
  type        = string
  default     = ""
}
