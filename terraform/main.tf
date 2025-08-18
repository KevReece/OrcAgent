terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure AWS provider with region
provider "aws" {
  region = var.aws_region
}

# Local values for workspace-specific naming
locals {
  # Use workspace name as account_environment (test or sandbox)
  account_environment = terraform.workspace
  
  # Validate workspace is one of the expected values
  valid_workspaces = ["test", "sandbox"]
  workspace_valid = contains(local.valid_workspaces, terraform.workspace)
  
  # Error if workspace is not valid
  workspace_validation = local.workspace_valid ? null : tobool("ERROR: Workspace '${terraform.workspace}' is not valid. Use 'test' or 'sandbox'")
}

# Call the aws-fargate-stack module with workspace-specific configuration
module "aws_fargate_stack" {
  source = "./modules/aws-fargate-stack"
  
  # Pass workspace name as project_name for resource naming
  project_name = local.account_environment
  aws_region   = var.aws_region
  environments = var.app_environments
  
  # Pass through all other variables
  container_port             = var.container_port
  cpu                       = var.cpu
  memory                    = var.memory
  enable_container_insights = var.enable_container_insights
  log_retention_days        = var.log_retention_days
  
  # Add workspace-specific tags
  tags = merge(var.tags, {
    AccountEnvironment = local.account_environment
    Workspace         = terraform.workspace
  })
} 