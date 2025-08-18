"""
AWS CLI Tools for Fargate Management

Provides tools for AWS CLI operations like getting logs from deployed instances,
checking deployment health, and managing AWS resources.
Uses environment variables to determine test vs sandbox configuration.
"""

import os
import subprocess
import json
import requests
from dotenv import load_dotenv
from logger.log_wrapper import get_logger
from tools.context import ToolsContext

# Load environment variables from .env file
load_dotenv(override=True)


def get_tools(tools_context: ToolsContext):
    """AWS CLI Tools for Fargate Management"""
    
    def init(self, work_dir: str, is_integration_test: bool = False):
        """
        Initialize AWS CLI Tools.
        
        Args:
            work_dir: Working directory for agent operations
            is_integration_test: If True, uses test account environment variables
        """
        self.work_dir = work_dir
        self.is_integration_test = is_integration_test
        
        # Determine account environment (sandbox vs test)
        self.account_environment = "sandbox"
        if is_integration_test:
            self.account_environment = "test"
        
        self.logger = get_logger("tool:aws", __name__)
        self.logger.info(f"AWS CLI Tools initialized for account_environment: {self.account_environment}")
        
        # Use account-specific environment variables
        self.aws_region = os.getenv("AWS_DEFAULT_REGION")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if is_integration_test:
            self.aws_region = os.getenv("TEST_AWS_DEFAULT_REGION")
            self.aws_access_key_id = os.getenv("TEST_AWS_ACCESS_KEY_ID")
            self.aws_secret_access_key = os.getenv("TEST_AWS_SECRET_ACCESS_KEY")

    def _get_aws_env() -> dict:
        """
        Get environment variables for AWS CLI subprocess calls.
        
        Returns:
            dict: Environment variables with proper AWS credentials
        """
        env = os.environ.copy()
        
        # Override with the appropriate AWS credentials
        if self.aws_region:
            env["AWS_DEFAULT_REGION"] = self.aws_region
        if self.aws_access_key_id:
            env["AWS_ACCESS_KEY_ID"] = self.aws_access_key_id
        if self.aws_secret_access_key:
            env["AWS_SECRET_ACCESS_KEY"] = self.aws_secret_access_key
            
        return env
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir, tools_context.is_integration_test)
    self._get_aws_env = _get_aws_env

    def aws_get_fargate_logs(app_environment: str = "dev") -> str:
        """
        Get last 5 minutes of logs from AWS Fargate containers using AWS CLI.
        
        Args:
            app_environment: App environment to get logs from. Valid values: 'dev', 'test', 'prod' (default: 'dev')
        
        Returns:
            String containing the log output or error message
        """
        try:
            aws_region = self.aws_region
            
            if not aws_region:
                return "AWS_DEFAULT_REGION environment variable not set"
            
            if app_environment not in ['dev', 'test', 'prod']:
                return f"Invalid app_environment: {app_environment}. Must be dev, test, or prod."
            
            self.logger.info(f"Getting logs from account_environment: {self.account_environment}, app_environment: {app_environment} in region {aws_region}")
            
            # Get log group name with correct naming pattern
            log_group = f"/ecs/{self.account_environment}-{app_environment}"
            
            # Build AWS CLI command
            cmd = [
                "aws", "logs", "tail", log_group,
                "--region", aws_region,
                "--since", "5m"  # Last 5 minutes of logs
            ]
            
            self.logger.info(f"Retrieving logs from: {log_group}")
            
            # For one-time retrieval, capture output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=self._get_aws_env())
            
            if result.returncode == 0:
                if result.stdout.strip():
                    self.logger.info("Logs retrieved successfully!")
                    return result.stdout
                else:
                    return f"No recent logs found in {log_group}"
            else:
                error_msg = result.stderr or "Unknown error"
                if "ResourceNotFoundException" in error_msg:
                    return f"Log group {log_group} not found. Deploy an application first."
                else:
                    return f"Failed to get logs: {error_msg}"
                        
        except subprocess.TimeoutExpired:
            return "Timeout: Log retrieval took too long"
        except Exception as e:
            return f"Error getting logs: {str(e)}"

    def aws_get_service_health(app_environment: str = "dev") -> str:
        """
        Get health status of AWS Fargate service in the specified app environment.
        
        Args:
            app_environment (str): App environment to check. Valid values: 'dev', 'test', 'prod' (default: 'dev')
        
        Returns:
            str: Health status information or error message
        """
        try:
            # Use consistent naming pattern
            cluster_name = f"{self.account_environment}-{app_environment}"
            service_name = f"{self.account_environment}-{app_environment}-service"
            
            self.logger.info(f"Checking service health for account_environment: {self.account_environment}, app_environment: {app_environment} - Cluster: {cluster_name}, Service: {service_name}")
            
            # Get service details
            service_cmd = [
                "aws", "ecs", "describe-services",
                "--cluster", cluster_name,
                "--services", service_name
            ]
            
            service_result = subprocess.run(
                service_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            service_data = json.loads(service_result.stdout)
            services = service_data.get('services', [])
            
            if not services:
                return f"Service {service_name} not found in cluster {cluster_name}"
            
            service = services[0]
            
            # Extract key health information
            status = service.get('status', 'UNKNOWN')
            running_count = service.get('runningCount', 0)
            pending_count = service.get('pendingCount', 0)
            desired_count = service.get('desiredCount', 0)
            
            health_info = [
                f"Service Health for {self.account_environment}-{app_environment}:",
                f"   Status: {status}",
                f"   Running Tasks: {running_count}/{desired_count}",
                f"   Pending Tasks: {pending_count}",
            ]
            
            # Get task details if running
            if running_count > 0:
                tasks_cmd = [
                    "aws", "ecs", "list-tasks",
                    "--cluster", cluster_name,
                    "--service-name", service_name
                ]
                
                tasks_result = subprocess.run(
                    tasks_cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=self._get_aws_env()
                )
                
                tasks_data = json.loads(tasks_result.stdout)
                task_arns = tasks_data.get('taskArns', [])
                
                if task_arns:
                    # Get detailed task information
                    describe_tasks_cmd = [
                        "aws", "ecs", "describe-tasks",
                        "--cluster", cluster_name,
                        "--tasks"
                    ] + task_arns
                    
                    describe_result = subprocess.run(
                        describe_tasks_cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        env=self._get_aws_env()
                    )
                    
                    tasks_details = json.loads(describe_result.stdout)
                    tasks_info = tasks_details.get('tasks', [])
                    
                    health_info.append("   Tasks:")
                    for task in tasks_info:
                        task_def = task.get('taskDefinitionArn', '').split('/')[-1]
                        last_status = task.get('lastStatus', 'UNKNOWN')
                        health_status = task.get('healthStatus', 'UNKNOWN')
                        health_info.append(f"     - {task_def}: {last_status} (Health: {health_status})")
            
            return "\n".join(health_info)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "ClusterNotFoundException" in error_msg:
                return f"Cluster {cluster_name} not found. Infrastructure may not be deployed."
            elif "ServiceNotFoundException" in error_msg:
                return f"Service {service_name} not found. Application may not be deployed."
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error checking service health: {str(e)}"

    def aws_get_load_balancer_url(app_environment: str = "dev") -> str:
        """
        Get the load balancer URL for the specified app environment.
        
        Args:
            app_environment (str): App environment to get URL for. Valid values: 'dev', 'test', 'prod' (default: 'dev')
        
        Returns:
            str: Load balancer URL or error message
        """
        try:
            # Use consistent naming pattern
            load_balancer_name = f"{self.account_environment}-{app_environment}-alb"
            
            self.logger.info(f"Getting load balancer URL for account_environment: {self.account_environment}, app_environment: {app_environment} - Load balancer: {load_balancer_name}")
            
            # Get load balancer details
            lb_cmd = [
                "aws", "elbv2", "describe-load-balancers",
                "--names", load_balancer_name
            ]
            
            lb_result = subprocess.run(
                lb_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            lb_data = json.loads(lb_result.stdout)
            load_balancers = lb_data.get('LoadBalancers', [])
            
            if not load_balancers:
                return f"Load balancer {load_balancer_name} not found"
            
            lb = load_balancers[0]
            dns_name = lb.get('DNSName', '')
            scheme = lb.get('Scheme', 'internet-facing')
            state = lb.get('State', {}).get('Code', 'unknown')
            
            if not dns_name:
                return f"No DNS name found for load balancer {load_balancer_name}"
            
            # Construct URL (assuming HTTP for now)
            url = f"http://{dns_name}"
            
            result_info = [
                f"🔗 Load Balancer URL for {self.account_environment}-{app_environment}:",
                f"   URL: {url}",
                f"   DNS: {dns_name}",
                f"   Scheme: {scheme}",
                f"   State: {state}"
            ]
            
            return "\n".join(result_info)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "LoadBalancerNotFound" in error_msg:
                return f"⚠️ Load balancer {load_balancer_name} not found. Infrastructure may not be deployed."
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "❌ Error parsing AWS CLI response"
        except Exception as e:
            return f"Error getting load balancer URL: {str(e)}"

    def aws_list_ecr_images() -> str:
        """
        List Docker images in the ECR repository.
        
        Returns:
            str: List of images or error message
        """
        try:
            # Use consistent naming pattern
            repository_name = f"{self.account_environment}-ecr"
            
            self.logger.info(f"Listing ECR images for account_environment: {self.account_environment} - Repository: {repository_name}")
            
            # Get ECR images
            ecr_cmd = [
                "aws", "ecr", "describe-images",
                "--repository-name", repository_name,
                "--output", "json"
            ]
            
            ecr_result = subprocess.run(
                ecr_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            ecr_data = json.loads(ecr_result.stdout)
            images = ecr_data.get('imageDetails', [])
            
            if not images:
                return f"ECR Images in {repository_name}: No images found"
            
            result_lines = [f"ECR Images in {repository_name}:"]
            
            # Sort images by push date (newest first)
            sorted_images = sorted(images, key=lambda x: x.get('imagePushedAt', ''), reverse=True)
            
            for image in sorted_images:
                tags = image.get('imageTags', ['<untagged>'])
                size_mb = round(image.get('imageSizeInBytes', 0) / (1024 * 1024), 1)
                pushed_at = image.get('imagePushedAt', 'Unknown')
                
                for tag in tags:
                    result_lines.append(f"   {tag} ({size_mb} MB) - {pushed_at}")
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "RepositoryNotFoundException" in error_msg:
                return f"ECR repository {repository_name} not found. Infrastructure may not be deployed."
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error listing ECR images: {str(e)}"

    def aws_get_ecs_service_events(app_environment: str = "dev") -> str:
        """
        Get ECS service events which show deployment failures, task placement issues, etc.
        
        Args:
            app_environment (str): App environment to check. Valid values: 'dev', 'test', 'prod' (default: 'dev')
        
        Returns:
            str: Service events information or error message
        """
        try:
            # Use consistent naming pattern
            cluster_name = f"{self.account_environment}-{app_environment}"
            service_name = f"{self.account_environment}-{app_environment}-service"
            
            self.logger.info(f"Getting service events for account_environment: {self.account_environment}, app_environment: {app_environment} - Cluster: {cluster_name}, Service: {service_name}")
            
            # Get service details with events
            service_cmd = [
                "aws", "ecs", "describe-services",
                "--cluster", cluster_name,
                "--services", service_name,
                "--output", "json"
            ]
            
            service_result = subprocess.run(
                service_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            service_data = json.loads(service_result.stdout)
            services = service_data.get('services', [])
            
            if not services:
                return f"Service {service_name} not found in cluster {cluster_name}"
            
            service = services[0]
            events = service.get('events', [])
            
            if not events:
                return f"No recent events found for service {service_name}"
            
            result_lines = [f"ECS Service Events for {self.account_environment}-{app_environment}:"]
            
            # Show last 10 events (most recent first)
            recent_events = events[:10]
            
            for event in recent_events:
                message = event.get('message', 'No message')
                created_at = event.get('createdAt', 'Unknown')
                id_info = event.get('id', 'No ID')
                
                result_lines.append(f"   [{created_at}] {id_info}: {message}")
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "ClusterNotFoundException" in error_msg:
                return f"Cluster {cluster_name} not found. Infrastructure may not be deployed."
            elif "ServiceNotFoundException" in error_msg:
                return f"Service {service_name} not found. Application may not be deployed."
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error getting service events: {str(e)}"

    def aws_get_failed_task_details(app_environment: str = "dev") -> str:
        """
        Get detailed information about failed ECS tasks including stop reasons and exit codes.
        
        Args:
            app_environment (str): App environment to check. Valid values: 'dev', 'test', 'prod' (default: 'dev')
        
        Returns:
            str: Failed task details or error message
        """
        try:
            # Use consistent naming pattern
            cluster_name = f"{self.account_environment}-{app_environment}"
            
            self.logger.info(f"Getting failed task details for account_environment: {self.account_environment}, app_environment: {app_environment} - Cluster: {cluster_name}")
            
            # List all tasks (including stopped ones)
            list_tasks_cmd = [
                "aws", "ecs", "list-tasks",
                "--cluster", cluster_name,
                "--desired-status", "STOPPED",
                "--output", "json"
            ]
            
            list_result = subprocess.run(
                list_tasks_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            tasks_data = json.loads(list_result.stdout)
            task_arns = tasks_data.get('taskArns', [])
            
            if not task_arns:
                return f"No stopped tasks found in cluster {cluster_name}"
            
            # Get detailed information for failed tasks
            describe_tasks_cmd = [
                "aws", "ecs", "describe-tasks",
                "--cluster", cluster_name,
                "--tasks"
            ] + task_arns
            
            describe_result = subprocess.run(
                describe_tasks_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            tasks_details = json.loads(describe_result.stdout)
            tasks = tasks_details.get('tasks', [])
            
            result_lines = [f"Failed Task Details for {self.account_environment}-{app_environment}:"]
            
            # Filter for failed tasks and show details
            failed_tasks = [task for task in tasks if task.get('lastStatus') == 'STOPPED']
            
            if not failed_tasks:
                return f"No failed tasks found in cluster {cluster_name}"
            
            for task in failed_tasks[:5]:  # Limit to 5 most recent
                task_def = task.get('taskDefinitionArn', '').split('/')[-1]
                stop_reason = task.get('stoppedReason', 'Unknown')
                stop_code = task.get('stoppedAt', 'Unknown')
                
                result_lines.append(f"   Task Definition: {task_def}")
                result_lines.append(f"   Stop Reason: {stop_reason}")
                result_lines.append(f"   Stopped At: {stop_code}")
                
                # Get container details
                containers = task.get('containers', [])
                for container in containers:
                    container_name = container.get('name', 'Unknown')
                    exit_code = container.get('exitCode', 'Unknown')
                    reason = container.get('reason', 'Unknown')
                    
                    result_lines.append(f"     Container {container_name}: Exit Code {exit_code}, Reason: {reason}")
                
                result_lines.append("")  # Empty line between tasks
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "ClusterNotFoundException" in error_msg:
                return f"Cluster {cluster_name} not found. Infrastructure may not be deployed."
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error getting failed task details: {str(e)}"

    def aws_get_task_execution_logs(app_environment: str = "dev", time_range: str = "1h") -> str:
        """
        Get task execution logs including ECS agent logs, image pull failures, and container startup logs.
        
        Args:
            app_environment (str): App environment to check. Valid values: 'dev', 'test', 'prod' (default: 'dev')
            time_range (str): Time range for logs (e.g., '5m', '1h', '1d'). Default: '1h'
        
        Returns:
            str: Task execution logs or error message
        """
        try:
            aws_region = self.aws_region
            
            if not aws_region:
                return "AWS_DEFAULT_REGION environment variable not set"
            
            if app_environment not in ['dev', 'test', 'prod']:
                return f"Invalid app_environment: {app_environment}. Must be dev, test, or prod."
            
            self.logger.info(f"Getting task execution logs from account_environment: {self.account_environment}, app_environment: {app_environment} in region {aws_region}")
            
            # Get log group name with correct naming pattern
            log_group = f"/ecs/{self.account_environment}-{app_environment}"
            
            # Build AWS CLI command
            cmd = [
                "aws", "logs", "tail", log_group,
                "--region", aws_region,
                "--since", time_range
            ]
            
            self.logger.info(f"Retrieving task execution logs from: {log_group} for last {time_range}")
            
            # For one-time retrieval, capture output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=self._get_aws_env())
            
            if result.returncode == 0:
                if result.stdout.strip():
                    self.logger.info("Task execution logs retrieved successfully!")
                    return result.stdout
                else:
                    return f"No recent task execution logs found in {log_group} for the last {time_range}"
            else:
                error_msg = result.stderr or "Unknown error"
                if "ResourceNotFoundException" in error_msg:
                    return f"Log group {log_group} not found. Deploy an application first."
                else:
                    return f"Failed to get task execution logs: {error_msg}"
                        
        except subprocess.TimeoutExpired:
            return "Timeout: Task execution log retrieval took too long"
        except Exception as e:
            return f"Error getting task execution logs: {str(e)}"

    def aws_inspect_task_definition(task_definition_family: str) -> str:
        """
        Inspect ECS task definition details including containers, images, and configuration.
        
        Args:
            task_definition_family (str): Task definition family name (e.g., 'sandbox-dev')
        
        Returns:
            str: Task definition details or error message
        """
        try:
            self.logger.info(f"Inspecting task definition: {task_definition_family}")
            
            # Get task definition details
            cmd = [
                "aws", "ecs", "describe-task-definition",
                "--task-definition", task_definition_family,
                "--output", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            task_data = json.loads(result.stdout)
            task_def = task_data.get('taskDefinition', {})
            
            if not task_def:
                return f"Task definition {task_definition_family} not found"
            
            # Extract key information
            family = task_def.get('family', 'Unknown')
            revision = task_def.get('revision', 'Unknown')
            status = task_def.get('status', 'Unknown')
            containers = task_def.get('containerDefinitions', [])
            
            result_lines = [
                f"Task Definition Inspection for {task_definition_family}:",
                f"   Family: {family}",
                f"   Revision: {revision}",
                f"   Status: {status}",
                f"   Containers: {len(containers)}"
            ]
            
            # Show container details
            for i, container in enumerate(containers, 1):
                name = container.get('name', 'Unknown')
                image = container.get('image', 'Unknown')
                cpu = container.get('cpu', 'Unknown')
                memory = container.get('memory', 'Unknown')
                port_mappings = container.get('portMappings', [])
                
                result_lines.append(f"   Container {i}:")
                result_lines.append(f"     Name: {name}")
                result_lines.append(f"     Image: {image}")
                result_lines.append(f"     CPU: {cpu}")
                result_lines.append(f"     Memory: {memory}")
                
                if port_mappings:
                    ports = [f"{pm.get('containerPort', '?')}->{pm.get('hostPort', '?')}" for pm in port_mappings]
                    result_lines.append(f"     Ports: {', '.join(ports)}")
                
                result_lines.append("")
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "TaskDefinitionNotFoundException" in error_msg:
                return f"Task definition {task_definition_family} not found"
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error inspecting task definition: {str(e)}"

    def aws_discover_container_names(task_definition_family: str) -> str:
        """
        Discover container names from an ECS task definition.
        
        Args:
            task_definition_family (str): Task definition family name (e.g., 'sandbox-dev')
        
        Returns:
            str: List of container names or error message
        """
        try:
            self.logger.info(f"Discovering container names for task definition: {task_definition_family}")
            
            # Get task definition details
            cmd = [
                "aws", "ecs", "describe-task-definition",
                "--task-definition", task_definition_family,
                "--query", "taskDefinition.containerDefinitions[].name",
                "--output", "text"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            container_names = result.stdout.strip().split('\n')
            
            if not container_names or container_names == ['']:
                return f"No containers found in task definition {task_definition_family}"
            
            result_lines = [f"Container names in {task_definition_family}:"]
            for name in container_names:
                if name.strip():
                    result_lines.append(f"   - {name.strip()}")
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "TaskDefinitionNotFoundException" in error_msg:
                return f"Task definition {task_definition_family} not found"
            return f"AWS CLI error: {error_msg}"
        except Exception as e:
            return f"Error discovering container names: {str(e)}"

    def aws_verify_ecr_image(repository_name: str, image_tag: str) -> str:
        """
        Verify that a specific Docker image exists in ECR repository.
        
        Args:
            repository_name (str): ECR repository name (e.g., 'sandbox-ecr')
            image_tag (str): Image tag to verify (e.g., 'latest', commit SHA)
        
        Returns:
            str: Image verification result or error message
        """
        try:
            self.logger.info(f"Verifying ECR image: {repository_name}:{image_tag}")
            
            # Check if image exists
            cmd = [
                "aws", "ecr", "describe-images",
                "--repository-name", repository_name,
                "--image-ids", f"imageTag={image_tag}",
                "--output", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            image_data = json.loads(result.stdout)
            images = image_data.get('imageDetails', [])
            
            if not images:
                return f"Image {repository_name}:{image_tag} not found in ECR"
            
            image = images[0]
            size_mb = round(image.get('imageSizeInBytes', 0) / (1024 * 1024), 1)
            pushed_at = image.get('imagePushedAt', 'Unknown')
            digest = image.get('imageDigest', 'Unknown')
            
            result_lines = [
                f"ECR Image Verification for {repository_name}:{image_tag}:",
                f"   Status: ✅ FOUND",
                f"   Size: {size_mb} MB",
                f"   Pushed: {pushed_at}",
                f"   Digest: {digest[:20]}..."
            ]
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "ImageNotFoundException" in error_msg:
                return f"❌ Image {repository_name}:{image_tag} not found in ECR"
            elif "RepositoryNotFoundException" in error_msg:
                return f"❌ ECR repository {repository_name} not found"
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error verifying ECR image: {str(e)}"

    def aws_check_service_scaling(cluster_name: str, service_name: str) -> str:
        """
        Check the scaling status of an ECS service.
        
        Args:
            cluster_name (str): ECS cluster name (e.g., 'sandbox-dev')
            service_name (str): ECS service name (e.g., 'sandbox-dev-service')
        
        Returns:
            str: Service scaling status or error message
        """
        try:
            self.logger.info(f"Checking service scaling for {cluster_name}/{service_name}")
            
            # Get service details
            cmd = [
                "aws", "ecs", "describe-services",
                "--cluster", cluster_name,
                "--services", service_name,
                "--output", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env()
            )
            
            service_data = json.loads(result.stdout)
            services = service_data.get('services', [])
            
            if not services:
                return f"Service {service_name} not found in cluster {cluster_name}"
            
            service = services[0]
            status = service.get('status', 'UNKNOWN')
            desired_count = service.get('desiredCount', 0)
            running_count = service.get('runningCount', 0)
            pending_count = service.get('pendingCount', 0)
            
            result_lines = [
                f"Service Scaling Status for {cluster_name}/{service_name}:",
                f"   Status: {status}",
                f"   Desired Count: {desired_count}",
                f"   Running Count: {running_count}",
                f"   Pending Count: {pending_count}"
            ]
            
            # Add scaling analysis
            if desired_count == 0:
                result_lines.append("   ⚠️  Service is scaled to 0 - no traffic will be served")
            elif running_count == 0 and desired_count > 0:
                result_lines.append("   ⚠️  Service has no running tasks despite desired count > 0")
            elif running_count == desired_count:
                result_lines.append("   ✅ Service is properly scaled")
            else:
                result_lines.append("   ⚠️  Service scaling is in progress or has issues")
            
            return "\n".join(result_lines)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else 'Command failed'
            if "ClusterNotFoundException" in error_msg:
                return f"❌ Cluster {cluster_name} not found"
            elif "ServiceNotFoundException" in error_msg:
                return f"❌ Service {service_name} not found in cluster {cluster_name}"
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "Error parsing AWS CLI response"
        except Exception as e:
            return f"Error checking service scaling: {str(e)}"

    
    def aws_validate_route(app_environment: str = "dev", relative_path: str = "/") -> str:
        """
        Validate that a given HTTP route on the environment responds successfully.

        Args:
            app_environment: App environment to probe. One of 'dev', 'test', 'prod' (default: 'dev')
            relative_path: Relative path to probe (e.g., '/', '/health', 'api/status')

        Returns:
            str: PASS/FAIL summary including URL and HTTP status
        """
        try:
            if app_environment not in ["dev", "test", "prod"]:
                return f"Invalid app_environment: {app_environment}. Must be dev, test, or prod."

            # Determine load balancer name and fetch DNS
            load_balancer_name = f"{self.account_environment}-{app_environment}-alb"
            self.logger.info(
                f"Validating route for account_environment: {self.account_environment}, app_environment: {app_environment}, lb: {load_balancer_name}, path: {relative_path}"
            )

            lb_cmd = [
                "aws",
                "elbv2",
                "describe-load-balancers",
                "--names",
                load_balancer_name,
            ]

            lb_result = subprocess.run(
                lb_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=self._get_aws_env(),
            )

            lb_data = json.loads(lb_result.stdout)
            load_balancers = lb_data.get("LoadBalancers", [])
            if not load_balancers:
                return f"Load balancer {load_balancer_name} not found"

            dns_name = load_balancers[0].get("DNSName", "")
            if not dns_name:
                return f"No DNS name found for load balancer {load_balancer_name}"

            # Normalize path and build URL (assume HTTP listener)
            path = relative_path if relative_path.startswith("/") else f"/{relative_path}"
            url = f"http://{dns_name}{path}"

            # Perform HTTP GET
            self.logger.info(f"Probing URL: {url}")
            try:
                response = requests.get(url, timeout=10)
                status = response.status_code
                passed = 200 <= status < 400
                outcome = "PASS" if passed else "FAIL"
                return "\n".join(
                    [
                        f"Route Validation for {self.account_environment}-{app_environment}:",
                        f"   URL: {url}",
                        f"   HTTP Status: {status}",
                        f"   Result: {'✅ ' if passed else '❌ '}{outcome}",
                    ]
                )
            except requests.Timeout:
                return "\n".join(
                    [
                        f"Route Validation for {self.account_environment}-{app_environment}:",
                        f"   URL: {url}",
                        "   Result: ❌ FAIL (Timeout)",
                    ]
                )
            except requests.RequestException as e:
                return "\n".join(
                    [
                        f"Route Validation for {self.account_environment}-{app_environment}:",
                        f"   URL: {url}",
                        f"   Result: ❌ FAIL ({str(e)})",
                    ]
                )

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else "Command failed"
            if "LoadBalancerNotFound" in error_msg:
                return f"⚠️ Load balancer {self.account_environment}-{app_environment}-alb not found. Infrastructure may not be deployed."
            return f"AWS CLI error: {error_msg}"
        except json.JSONDecodeError:
            return "❌ Error parsing AWS CLI response"
        except Exception as e:
            return f"Error validating route: {str(e)}"

 
    # Return list of tools
    return [
        aws_get_fargate_logs,
        aws_get_service_health,
        aws_get_load_balancer_url,
        aws_list_ecr_images,
        aws_get_ecs_service_events,
        aws_get_failed_task_details,
        aws_get_task_execution_logs,
        aws_inspect_task_definition,
        aws_discover_container_names,
        aws_verify_ecr_image,
        aws_check_service_scaling,
        aws_validate_route,
    ] 