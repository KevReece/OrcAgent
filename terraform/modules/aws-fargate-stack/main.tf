terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources for existing resources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  # Use the project name from variables (no auto-detection)
  project_name = var.project_name
  
  # Merge user-provided tags with defaults
  common_tags = merge(
    {
      Project   = local.project_name
      ManagedBy = "terraform"
      CreatedBy = "orc_agent_${local.project_name}"
    },
    var.tags
  )
  
  # Sanitize project name for AWS resources that don't allow underscores
  sanitized_project_name = replace(local.project_name, "_", "-")
}

# ECR Repository
resource "aws_ecr_repository" "app_repo" {
  name                 = "${local.project_name}-ecr"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_lifecycle_policy" "app_repo_policy" {
  repository = aws_ecr_repository.app_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 30 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-igw"
  })
}

# Public Subnets
resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-public-subnet-${count.index + 1}"
  })
}

# Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-public-rt"
  })
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  name_prefix = "${local.project_name}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-alb-sg"
  })
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${local.project_name}-ecs-tasks-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-ecs-tasks-sg"
  })
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  count = length(var.environments)
  name  = "${local.project_name}-${var.environments[count.index]}"

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs[count.index].name
      }
    }
  }

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = merge(local.common_tags, {
    Name        = "${local.project_name}-${var.environments[count.index]}-cluster"
    Environment = var.environments[count.index]
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs" {
  count             = length(var.environments)
  name              = "/ecs/${local.project_name}-${var.environments[count.index]}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Environment = var.environments[count.index]
  })
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task" {
  name = "${local.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for ECS Task
resource "aws_iam_role_policy" "ecs_task" {
  name = "${local.project_name}-ecs-task-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "app" {
  count                    = length(var.environments)
  family                   = "${local.project_name}-${var.environments[count.index]}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "${local.project_name}-app"
      image = "${aws_ecr_repository.app_repo.repository_url}:latest"

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs[count.index].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environments[count.index]
        }
      ]

      essential = true
    }
  ])

  tags = merge(local.common_tags, {
    Environment = var.environments[count.index]
  })
}

# Application Load Balancers
resource "aws_lb" "main" {
  count              = length(var.environments)
  name               = "${local.sanitized_project_name}-${var.environments[count.index]}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Environment = var.environments[count.index]
  })
}

# Target Groups
resource "aws_lb_target_group" "app" {
  count       = length(var.environments)
  name        = "${local.sanitized_project_name}-${var.environments[count.index]}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Environment = var.environments[count.index]
  })
}

# Load Balancer Listeners
resource "aws_lb_listener" "app" {
  count             = length(var.environments)
  load_balancer_arn = aws_lb.main[count.index].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app[count.index].arn
  }

  tags = merge(local.common_tags, {
    Environment = var.environments[count.index]
  })
}

# ECS Services
resource "aws_ecs_service" "app" {
  count           = length(var.environments)
  name            = "${local.project_name}-${var.environments[count.index]}-service"
  cluster         = aws_ecs_cluster.main[count.index].id
  task_definition = aws_ecs_task_definition.app[count.index].arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.public[*].id
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app[count.index].arn
    container_name   = "${local.project_name}-app"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.app]

  tags = merge(local.common_tags, {
    Environment = var.environments[count.index]
  })
} 