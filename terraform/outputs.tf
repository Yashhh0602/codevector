output "alb_dns_name" {
  description = "Public URL for the API (HTTP only — see README before adding real traffic)"
  value       = aws_lb.this.dns_name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}
