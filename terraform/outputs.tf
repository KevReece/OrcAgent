# Pass through all outputs from the aws-fargate-stack module

# ECR Repository URL
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.aws_fargate_stack.ecr_repository_url
}

# ECS Cluster Names
output "ecs_cluster_names" {
  description = "ECS cluster names for each app environment"
  value       = module.aws_fargate_stack.ecs_cluster_names
}

# ECS Cluster ARNs
output "ecs_cluster_arns" {
  description = "ECS cluster ARNs for each app environment"
  value       = module.aws_fargate_stack.ecs_cluster_arns
}

# ECS Service Names
output "ecs_service_names" {
  description = "ECS service names for each app environment"
  value       = module.aws_fargate_stack.ecs_service_names
}

# ECS Service ARNs
output "ecs_service_arns" {
  description = "ECS service ARNs for each app environment"
  value       = module.aws_fargate_stack.ecs_service_arns
}

# Load Balancer DNS Names
output "load_balancer_dns_names" {
  description = "DNS names of the load balancers"
  value       = module.aws_fargate_stack.load_balancer_dns_names
}

# Load Balancer URLs
output "load_balancer_urls" {
  description = "URLs of the load balancers"
  value       = module.aws_fargate_stack.load_balancer_urls
}

# VPC ID
output "vpc_id" {
  description = "VPC ID"
  value       = module.aws_fargate_stack.vpc_id
}

# Subnet IDs
output "subnet_ids" {
  description = "Public subnet IDs"
  value       = module.aws_fargate_stack.subnet_ids
}

# Security Group IDs
output "security_group_ids" {
  description = "Security group IDs"
  value       = module.aws_fargate_stack.security_group_ids
}

# Task Definition ARNs
output "task_definition_arns" {
  description = "Task definition ARNs for each app environment"
  value       = module.aws_fargate_stack.task_definition_arns
}

# CloudWatch Log Group Names
output "cloudwatch_log_group_names" {
  description = "CloudWatch log group names for each app environment"
  value       = module.aws_fargate_stack.cloudwatch_log_group_names
}

# IAM Role ARNs
output "iam_role_arns" {
  description = "IAM role ARNs"
  value       = module.aws_fargate_stack.iam_role_arns
}

# Environment-specific outputs
output "app_environments" {
  description = "App environment configuration details"
  value       = module.aws_fargate_stack.environments
}

# Account environment (workspace) information
output "account_environment" {
  description = "Account environment (workspace) name"
  value       = terraform.workspace
}

# AWS region
output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
} 