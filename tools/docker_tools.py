"""
Docker Tools for AWS Fargate Deployment

Provides tools for building, pushing, and deploying Docker images to AWS Fargate environments.
Uses environment variables to determine test vs sandbox configuration.
"""

import os
import subprocess
import time
from datetime import datetime
from secrets import token_hex
from typing import Any, Dict, Optional

import boto3  # type: ignore
import requests  # type: ignore
from dotenv import load_dotenv
from logger.log_wrapper import get_logger
from tools.context import ToolsContext

load_dotenv(override=True)


def get_tools(tools_context: ToolsContext):
    """Docker Tools for AWS Fargate Deployment"""
    
    def init(self, work_dir: str, is_integration_test: bool = False):
        self.work_dir = work_dir
        self.is_integration_test = is_integration_test
        
        # Determine account environment (sandbox vs test)
        self.account_environment = "sandbox"
        if is_integration_test:
            self.account_environment = "test"
        
        self.logger = get_logger("tool:docker", __name__)
        self.logger.info(f"Docker Tools initialized for account_environment: {self.account_environment}")
        
        # Use account-specific environment variables
        self.aws_region = os.getenv("AWS_DEFAULT_REGION")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if is_integration_test:
            self.aws_region = os.getenv("TEST_AWS_DEFAULT_REGION")
            self.aws_access_key_id = os.getenv("TEST_AWS_ACCESS_KEY_ID")
            self.aws_secret_access_key = os.getenv("TEST_AWS_SECRET_ACCESS_KEY")
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir, tools_context.is_integration_test)

    def docker_build_image(source_directory: str = ".", image_name: str = "my-app", image_tag: str = "latest") -> Dict[str, Any]:
        """
        Build a Docker image from a Dockerfile in the specified directory.
        
        The Dockerfile should be compatible with the target platform of AWS Fargate.
        The build will be for linux/amd64 for Fargate compatibility.
        The AWS Fargate infrastructure expects web services on port 8080.
        
        Args:
            source_directory: Directory containing Dockerfile (relative to work_dir)
            image_name: Name for the Docker image
            image_tag: Tag for the Docker image
            
        Returns:
            Dict containing success status and message
        """
        build_path = os.path.join(self.work_dir, source_directory)
        
        if not os.path.exists(build_path):
            error_msg = f"Directory {source_directory} does not exist"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
        
        dockerfile_path = os.path.join(build_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            error_msg = f"Dockerfile not found in {source_directory}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
        
        try:
            self.logger.info(f"Building Docker image {image_name}:{image_tag} from {source_directory}")
            
            # Run docker build command with platform specification for AWS Fargate
            build_cmd = [
                "docker", "build", 
                "--platform", "linux/amd64",
                "-t", f"{image_name}:{image_tag}", 
                "."
            ]
            
            result = subprocess.run(
                build_cmd,
                cwd=build_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("Docker image built successfully")
                return {
                    "success": True,
                    "message": f"Successfully built image {image_name}:{image_tag}",
                    "image_name": image_name,
                    "image_tag": image_tag
                }
            else:
                error_msg = f"Docker build failed: {result.stderr}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "message": f"Error: Docker build failed - {result.stderr.strip()}"
                }
        except Exception as e:
            error_msg = f"Error building Docker image: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": f"Error building Docker image: {str(e)}"
            }

    def _docker_push_to_ecr(image_name: str = "app", image_tag: str = "latest") -> Dict[str, Any]:
        """
        Push a Docker image to AWS ECR.
        
        Args:
            image_name: Name of the image to push
            image_tag: Tag of the image to push
        
        Returns:
            Dictionary with success status and details
        """
        try:
            self.logger.info(f"Pushing Docker image {image_name}:{image_tag} to ECR for account_environment: {self.account_environment}")
            
            # Get ECR repository URL using the correct credentials
            ecr_client = boto3.client(
                'ecr',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            repo_name = f"{self.account_environment}-ecr"
            
            try:
                response = ecr_client.describe_repositories(repositoryNames=[repo_name])
                ecr_url = response['repositories'][0]['repositoryUri']
                self.logger.info(f"ECR URL: {ecr_url}")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"ECR repository not found: {e}",
                    "message": f"ECR repository {repo_name} not found. Run terraform apply first."
                }
            
            # Set up environment for AWS CLI commands
            aws_env = os.environ.copy()
            if self.aws_access_key_id:
                aws_env['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
            if self.aws_secret_access_key:
                aws_env['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
            if self.aws_region:
                aws_env['AWS_DEFAULT_REGION'] = self.aws_region
            
            # Get ECR login token
            if not self.aws_region:
                return {
                    "success": False,
                    "error": "AWS region not configured",
                    "message": "AWS region not configured. Check environment variables."
                }
            
            login_cmd = [
                "aws", "ecr", "get-login-password",
                "--region", self.aws_region
            ]
            
            login_result = subprocess.run(login_cmd, capture_output=True, text=True, timeout=60, env=aws_env)
            
            if login_result.returncode != 0:
                return {
                    "success": False,
                    "error": login_result.stderr,
                    "message": "Failed to get ECR login token"
                }
            
            # Docker login to ECR
            docker_login_cmd = [
                "docker", "login", "--username", "AWS",
                "--password-stdin", ecr_url.split('/')[0]
            ]
            
            login_process = subprocess.run(
                docker_login_cmd,
                input=login_result.stdout,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if login_process.returncode != 0:
                return {
                    "success": False,
                    "error": login_process.stderr,
                    "message": "Failed to login to ECR"
                }
            
            # Tag image for ECR
            tag_cmd = [
                "docker", "tag",
                f"{image_name}:{image_tag}",
                f"{ecr_url}:{image_tag}"
            ]
            
            tag_result = subprocess.run(tag_cmd, capture_output=True, text=True, timeout=60)
            
            if tag_result.returncode != 0:
                return {
                    "success": False,
                    "error": tag_result.stderr,
                    "message": "Failed to tag image for ECR"
                }
            
            # Push image to ECR
            push_cmd = [
                "docker", "push",
                f"{ecr_url}:{image_tag}"
            ]
            
            push_result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=300)
            
            if push_result.returncode == 0:
                self.logger.info("Docker image pushed successfully to ECR")
                return {
                    "success": True,
                    "message": f"Successfully pushed {image_name}:{image_tag} to ECR",
                    "ecr_url": ecr_url,
                    "image_uri": f"{ecr_url}:{image_tag}"
                }
            else:
                return {
                    "success": False,
                    "error": push_result.stderr,
                    "message": "Failed to push image to ECR"
                }
        except Exception as e:
            error_msg = f"Error pushing to ECR: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "message": "Error pushing to ECR"
            }

    def _wait_for_task_deployment(ecs_client, cluster_name: str, service_name: str, app_environment: str, task_definition_arn: str) -> Dict[str, Any]:
        """
        Wait for a task to come up after deployment with a 5-minute timeout.
        
        Args:
            ecs_client: ECS client instance
            cluster_name: Name of the ECS cluster
            service_name: Name of the ECS service
            app_environment: App environment being deployed to
            task_definition_arn: ARN of the task definition
            
        Returns:
            Dictionary with success status and deployment details
        """
        self.logger.info(f"Waiting for task to come up in {app_environment} environment...")
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check service status
                service_status = ecs_client.describe_services(
                    cluster=cluster_name,
                    services=[service_name]
                )
                
                if service_status['services']:
                    service = service_status['services'][0]
                    running_count = service['runningCount']
                    desired_count = service['desiredCount']
                    
                    self.logger.info(f"Running tasks: {running_count}/{desired_count}")
                    
                    if running_count >= desired_count and desired_count > 0:
                        self.logger.info(f"Task successfully deployed and running in {app_environment} environment")
                        return {
                            "success": True,
                            "task_definition": task_definition_arn,
                            "message": f"Successfully deployed to app_environment: {app_environment}",
                            "running_tasks": running_count,
                            "desired_tasks": desired_count
                        }
            except Exception as e:
                self.logger.warning(f"Error checking service status during wait: {e}")
            
            # Wait 10 seconds before checking again
            time.sleep(10)
        
        # Timeout reached
        self.logger.error(f"Timeout waiting for task to come up in {app_environment} environment")
        return {
            "success": False,
            "error": "Deployment timeout",
            "message": f"Deployment to {app_environment} environment timed out after 5 minutes"
        }

    def _docker_deploy_to_app_environment(image_tag: str = "latest", app_environment: str = "dev") -> Dict[str, Any]:
        """
        Deploy a Docker image to the specified app environment.
        
        Args:
            image_tag: Tag of the image to deploy
            app_environment: App environment to deploy to ('dev', 'test', 'prod')
        
        Returns:
            Dictionary with success status and details
        """
        try:
            self.logger.info(f"Deploying to account_environment: {self.account_environment}, app_environment: {app_environment}")
            self.logger.info(f"Image tag: {image_tag}")
            
            # Get the ECR repository URL using the correct credentials
            ecr_client = boto3.client(
                'ecr',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            repo_name = f"{self.account_environment}-ecr"
            
            try:
                response = ecr_client.describe_repositories(repositoryNames=[repo_name])
                ecr_url = response['repositories'][0]['repositoryUri']
                image_uri = f"{ecr_url}:{image_tag}"
                self.logger.info(f"Image URI: {image_uri}")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"ECR repository not found: {e}",
                    "message": f"ECR repository {repo_name} not found. Run terraform apply first."
                }
            
            # Update the Fargate service with the new image
            ecs_client = boto3.client(
                'ecs',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            elbv2_client = boto3.client(
                'elbv2',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            logs_client = boto3.client(
                'logs',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            
            # Get current task definition
            cluster_name = f"{self.account_environment}-{app_environment}"
            service_name = f"{self.account_environment}-{app_environment}-service"
            
            try:
                # Get current service
                service_response = ecs_client.describe_services(
                    cluster=cluster_name,
                    services=[service_name]
                )
                
                if not service_response['services']:
                    return {
                        "success": False,
                        "error": f"Service {service_name} not found",
                        "message": f"Service {service_name} not found in cluster {cluster_name}"
                    }
                
                service_obj = service_response['services'][0]
                current_task_def_arn = service_obj['taskDefinition']
                
                # Get current task definition
                task_def_response = ecs_client.describe_task_definition(
                    taskDefinition=current_task_def_arn
                )
                
                # Create new task definition with updated image
                current_task_def = task_def_response['taskDefinition']
                
                # Extract logging details for diagnostics
                log_group_name: Optional[str] = None
                if current_task_def.get('containerDefinitions'):
                    first_container = current_task_def['containerDefinitions'][0]
                    log_config = first_container.get('logConfiguration', {})
                    options = log_config.get('options', {})
                    log_group_name = options.get('awslogs-group')

                # Update the container image
                new_container_defs = current_task_def['containerDefinitions'].copy()
                for container in new_container_defs:
                    container['image'] = image_uri
                
                # Create new task definition
                new_task_def = ecs_client.register_task_definition(
                    family=current_task_def['family'],
                    networkMode=current_task_def['networkMode'],
                    requiresCompatibilities=current_task_def['requiresCompatibilities'],
                    cpu=current_task_def['cpu'],
                    memory=current_task_def['memory'],
                    executionRoleArn=current_task_def['executionRoleArn'],
                    taskRoleArn=current_task_def.get('taskRoleArn'),
                    containerDefinitions=new_container_defs
                )
                
                # Update the service with new task definition
                ecs_client.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    taskDefinition=new_task_def['taskDefinition']['taskDefinitionArn'],
                    desiredCount=1
                )
                
                # Wait for the task to come up
                wait_result = _wait_for_task_deployment(
                    ecs_client, 
                    cluster_name, 
                    service_name, 
                    app_environment,
                    new_task_def['taskDefinition']['taskDefinitionArn']
                )
                
                if not wait_result.get('success'):
                    diagnostics = _collect_failure_diagnostics(
                        ecs_client=ecs_client,
                        logs_client=logs_client,
                        cluster_name=cluster_name,
                        service_name=service_name,
                        log_group_name=log_group_name,
                    )
                    wait_result['logs'] = diagnostics
                    return wait_result

                # Determine target group and load balancer URL
                target_group_arn: Optional[str] = None
                if service_obj.get('loadBalancers'):
                    target_group_arn = service_obj['loadBalancers'][0].get('targetGroupArn')

                if not target_group_arn:
                    return {
                        "success": False,
                        "error": "Target group not found",
                        "message": f"Failed to locate target group for service {service_name}",
                        "logs": _collect_failure_diagnostics(
                            ecs_client=ecs_client,
                            logs_client=logs_client,
                            cluster_name=cluster_name,
                            service_name=service_name,
                            log_group_name=log_group_name,
                        ),
                    }

                load_balancer_url = _resolve_load_balancer_url(elbv2_client, target_group_arn)
                if not load_balancer_url:
                    return {
                        "success": False,
                        "error": "Load balancer URL not found",
                        "message": "Unable to resolve load balancer DNS name",
                        "logs": _collect_failure_diagnostics(
                            ecs_client=ecs_client,
                            logs_client=logs_client,
                            cluster_name=cluster_name,
                            service_name=service_name,
                            log_group_name=log_group_name,
                        ),
                    }

                # Wait for ALB targets healthy and HTTP health endpoint to pass
                alb_wait = _wait_for_alb_health(
                    elbv2_client=elbv2_client,
                    target_group_arn=target_group_arn,
                    health_check_url=f"{load_balancer_url}/health",
                )

                if not alb_wait.get('success'):
                    alb_wait['logs'] = _collect_failure_diagnostics(
                        ecs_client=ecs_client,
                        logs_client=logs_client,
                        cluster_name=cluster_name,
                        service_name=service_name,
                        log_group_name=log_group_name,
                    )
                    return alb_wait

                return {
                    "success": True,
                    "task_definition": new_task_def['taskDefinition']['taskDefinitionArn'],
                    "message": f"Successfully deployed to app_environment: {app_environment}",
                    "running_tasks": wait_result.get('running_tasks'),
                    "desired_tasks": wait_result.get('desired_tasks'),
                    "load_balancer_url": load_balancer_url,
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to deploy to app_environment: {app_environment}: {e}"
                }
                
        except Exception as e:
            error_msg = f"Error deploying to app_environment: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "message": "Error deploying to app_environment"
            }

    def _resolve_load_balancer_url(elbv2_client, target_group_arn: str) -> Optional[str]:
        """Resolve the load balancer DNS name from a target group ARN and return http URL."""
        try:
            tg_desc = elbv2_client.describe_target_groups(TargetGroupArns=[target_group_arn])
            target_groups = tg_desc.get('TargetGroups', [])
            if not target_groups:
                return None
            lb_arns = target_groups[0].get('LoadBalancerArns', [])
            if not lb_arns:
                return None
            lb_desc = elbv2_client.describe_load_balancers(LoadBalancerArns=[lb_arns[0]])
            lbs = lb_desc.get('LoadBalancers', [])
            if not lbs:
                return None
            dns_name = lbs[0].get('DNSName')
            if not dns_name:
                return None
            return f"http://{dns_name}"
        except Exception:
            return None

    def _collect_failure_diagnostics(
        ecs_client,
        logs_client,
        cluster_name: str,
        service_name: str,
        log_group_name: Optional[str],
        max_events: int = 20,
        max_log_events: int = 100,
    ) -> Dict[str, Any]:
        """Collect ECS service events and recent CloudWatch Logs to aid troubleshooting."""
        diagnostics: Dict[str, Any] = {"ecs_events": [], "cloudwatch_logs": []}

        try:
            svc = ecs_client.describe_services(cluster=cluster_name, services=[service_name])
            if svc.get('services'):
                events = svc['services'][0].get('events', [])
                diagnostics["ecs_events"] = [
                    {"message": e.get('message'), "createdAt": e.get('createdAt')}
                    for e in events[:max_events]
                ]
        except Exception:
            pass

        if log_group_name:
            try:
                streams_resp = logs_client.describe_log_streams(
                    logGroupName=log_group_name,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=3,
                )
                streams = streams_resp.get('logStreams', [])
                for stream in streams:
                    stream_name = stream.get('logStreamName')
                    if not stream_name:
                        continue
                    events_resp = logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=stream_name,
                        limit=max_log_events,
                        startFromHead=False,
                    )
                    for ev in events_resp.get('events', [])[:max_log_events]:
                        diagnostics["cloudwatch_logs"].append({
                            "timestamp": ev.get('timestamp'),
                            "message": ev.get('message'),
                            "logStreamName": stream_name,
                        })
            except Exception:
                pass

        return diagnostics

    def _wait_for_alb_health(
        elbv2_client,
        target_group_arn: str,
        health_check_url: str,
        timeout_seconds: int = 300,
        poll_interval_seconds: int = 10,
    ) -> Dict[str, Any]:
        """Wait for target group health to be healthy and HTTP health endpoint to return 200."""
        self.logger.info("Waiting for ALB target health and HTTP /health endpoint...")
        deadline = time.time() + timeout_seconds
        last_http_error: Optional[str] = None

        while time.time() < deadline:
            try:
                th = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
                states = [d.get('TargetHealth', {}).get('State') for d in th.get('TargetHealthDescriptions', [])]
                all_healthy = bool(states) and all(s == 'healthy' for s in states)
            except Exception as e:
                all_healthy = False
                self.logger.warning(f"Error checking target health: {e}")

            http_ok = False
            try:
                resp = requests.get(health_check_url, timeout=5)
                http_ok = resp.status_code == 200
            except Exception as e:
                last_http_error = str(e)

            self.logger.info(f"ALB health check — targets healthy: {all_healthy}, http 200: {http_ok}")
            if all_healthy and http_ok:
                return {"success": True, "message": "ALB and HTTP health passed"}

            time.sleep(poll_interval_seconds)

        return {
            "success": False,
            "error": "ALB health timeout",
            "message": f"Timed out waiting for ALB target group to become healthy and HTTP health to pass. Last HTTP error: {last_http_error}",
        }

    # Note: Public deploy tool removed; use docker_build_push_deploy for end-to-end operations

    def docker_build_push_deploy(image_name: str = "app", image_tag: str = "latest", app_environment: str = "dev") -> Dict[str, Any]:
        """
        Build, push, and deploy a Docker image, and wait 5 mins for the task, in one operation.
        
        The Dockerfile should be compatible with the target platform of AWS Fargate.
        The build will be for linux/amd64 for Fargate compatibility.
        The AWS Fargate infrastructure expects web services on port 8080.

        Args:
            image_name: Name for the image
            image_tag: Tag for the image
            app_environment: App environment to deploy to ('dev', 'test', 'prod')
        
        Returns:
            Dictionary with operation results
        """
        try:
            # Generate a unique image tag when 'latest' (or empty) is requested to avoid stale deployments
            requested_tag = image_tag or "latest"
            if requested_tag == "latest":
                sha_env = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
                unique_suffix = (sha_env[:12] if sha_env else datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + token_hex(4))
                effective_tag = f"orcagent-{unique_suffix}"
                self.logger.info(f"Using unique image tag instead of 'latest': {effective_tag}")
            else:
                effective_tag = requested_tag

            # Build the image
            build_result = docker_build_image(image_name=image_name, image_tag=effective_tag)
            if not build_result['success']:
                return {"success": False, "message": f"Build failed: {build_result['message']}", "effective_image_tag": effective_tag}

            # Push to ECR
            push_result = _docker_push_to_ecr(image_name=image_name, image_tag=effective_tag)
            if not push_result['success']:
                return {"success": False, "message": f"Push failed: {push_result['message']}", "effective_image_tag": effective_tag}

            # Deploy to specified environment
            deploy_result = _docker_deploy_to_app_environment(effective_tag, app_environment)
            if not deploy_result['success']:
                merged_fail: Dict[str, Any] = {"success": False, "message": f"Deploy failed: {deploy_result['message']}", "effective_image_tag": effective_tag}
                for k, v in deploy_result.items():
                    if k not in {"success", "message"}:
                        merged_fail[k] = v
                return merged_fail

            # Include load balancer URL and other deployment details on success
            merged: Dict[str, Any] = {
                "success": True,
                "message": f"Successfully built, pushed, and deployed image {image_name}:{effective_tag} to {app_environment}",
                "effective_image_tag": effective_tag,
            }
            for k, v in deploy_result.items():
                if k not in merged:
                    merged[k] = v
            # Include image_uri from push if available
            if isinstance(push_result, dict) and push_result.get("image_uri"):
                merged["image_uri"] = push_result["image_uri"]
            return merged

        except Exception as e:
            return {"success": False, "message": f"Error in build-push-deploy: {str(e)}"}

    def docker_get_deployment_status(app_environment: str = "dev") -> str:
        """
        Get the current deployment status of the application.
        
        Args:
            app_environment: App environment to check ('dev', 'test', 'prod')
        
        Returns:
            String with deployment status information
        """
        try:
            ecs_client = boto3.client(
                'ecs',
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )
            
            cluster_name = f"{self.account_environment}-{app_environment}"
            service_name = f"{self.account_environment}-{app_environment}-service"
            
            self.logger.info(f"Getting deployment status for account_environment: {self.account_environment}, app_environment: {app_environment}")
            
            # Get service status
            service_response = ecs_client.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            if not service_response['services']:
                return f"Service {service_name} not found in cluster {cluster_name}"
            
            service = service_response['services'][0]
            
            # Get task definition details
            task_def_response = ecs_client.describe_task_definition(
                taskDefinition=service['taskDefinition']
            )
            
            task_def = task_def_response['taskDefinition']
            
            # Extract deployment info
            status_info = {
                "service_name": service_name,
                "cluster_name": cluster_name,
                "desired_count": service['desiredCount'],
                "running_count": service['runningCount'],
                "pending_count": service['pendingCount'],
                "task_definition": task_def['taskDefinitionArn'],
                "image": task_def['containerDefinitions'][0]['image'] if task_def['containerDefinitions'] else "Unknown"
            }
            
            return f"Deployment Status for {app_environment}:\n" + \
                   f"Service: {status_info['service_name']}\n" + \
                   f"Cluster: {status_info['cluster_name']}\n" + \
                   f"Running: {status_info['running_count']}/{status_info['desired_count']}\n" + \
                   f"Pending: {status_info['pending_count']}\n" + \
                   f"Task Definition: {status_info['task_definition']}\n" + \
                   f"Image: {status_info['image']}"
            
        except Exception as e:
            return f"Error getting deployment status: {str(e)}"
    
    # Return list of tools
    return [
        docker_build_image,
        docker_build_push_deploy,
        docker_get_deployment_status
    ]