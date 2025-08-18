variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project (determines resource prefixes)"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environments" {
  description = "List of environments to create"
  type        = list(string)
  default     = ["dev", "test", "prod"]
  validation {
    condition     = length(var.environments) > 0
    error_message = "At least one environment must be specified."
  }
}

variable "container_port" {
  description = "Port that the container listens on"
  type        = number
  default     = 8080
  validation {
    condition     = var.container_port > 0 && var.container_port < 65536
    error_message = "Container port must be between 1 and 65535."
  }
}

variable "cpu" {
  description = "CPU units for the ECS task"
  type        = string
  default     = "256"
  validation {
    condition     = contains(["256", "512", "1024", "2048", "4096"], var.cpu)
    error_message = "CPU must be one of: 256, 512, 1024, 2048, 4096."
  }
}

variable "memory" {
  description = "Memory for the ECS task"
  type        = string
  default     = "512"
  validation {
    condition     = contains(["512", "1024", "2048", "4096", "8192"], var.memory)
    error_message = "Memory must be one of: 512, 1024, 2048, 4096, 8192."
  }
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch log retention period."
  }
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
} 