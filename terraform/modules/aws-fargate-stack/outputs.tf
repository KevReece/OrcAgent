# ECR Repository URL
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app_repo.repository_url
}

# ECS Cluster Names
output "ecs_cluster_names" {
  description = "ECS cluster names for each environment"
  value       = aws_ecs_cluster.main[*].name
}

# ECS Cluster ARNs
output "ecs_cluster_arns" {
  description = "ECS cluster ARNs for each environment"
  value       = aws_ecs_cluster.main[*].arn
}

# ECS Service Names
output "ecs_service_names" {
  description = "ECS service names for each environment"
  value       = aws_ecs_service.app[*].name
}

# ECS Service ARNs
output "ecs_service_arns" {
  description = "ECS service ARNs for each environment"
  value       = aws_ecs_service.app[*].id
}

# Load Balancer DNS Names
output "load_balancer_dns_names" {
  description = "DNS names of the load balancers"
  value = {
    for i, env in var.environments : env => aws_lb.main[i].dns_name
  }
}

# Load Balancer URLs
output "load_balancer_urls" {
  description = "URLs of the load balancers"
  value = {
    for i, env in var.environments : env => "http://${aws_lb.main[i].dns_name}"
  }
}

# VPC ID
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

# Subnet IDs
output "subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

# Security Group IDs
output "security_group_ids" {
  description = "Security group IDs"
  value = {
    alb       = aws_security_group.alb.id
    ecs_tasks = aws_security_group.ecs_tasks.id
  }
}

# Task Definition ARNs
output "task_definition_arns" {
  description = "Task definition ARNs for each environment"
  value = {
    for i, env in var.environments : env => aws_ecs_task_definition.app[i].arn
  }
}

# CloudWatch Log Group Names
output "cloudwatch_log_group_names" {
  description = "CloudWatch log group names for each environment"
  value = {
    for i, env in var.environments : env => aws_cloudwatch_log_group.ecs[i].name
  }
}

# IAM Role ARNs
output "iam_role_arns" {
  description = "IAM role ARNs"
  value = {
    task_execution = aws_iam_role.ecs_task_execution.arn
    task           = aws_iam_role.ecs_task.arn
  }
}

# Environment-specific outputs
output "environments" {
  description = "Environment configuration details"
  value = {
    for i, env in var.environments : env => {
      cluster_name      = aws_ecs_cluster.main[i].name
      cluster_arn       = aws_ecs_cluster.main[i].arn
      service_name      = aws_ecs_service.app[i].name
      service_arn       = aws_ecs_service.app[i].id
      task_definition   = aws_ecs_task_definition.app[i].arn
      load_balancer_url = "http://${aws_lb.main[i].dns_name}"
      log_group         = aws_cloudwatch_log_group.ecs[i].name
    }
  }
} 