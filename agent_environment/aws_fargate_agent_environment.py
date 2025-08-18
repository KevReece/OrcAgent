"""
AWS Fargate Management Module

This module provides functionality to manage AWS Fargate deployments using
Terraform workspaces, with environment variable-based configuration for
test and sandbox account environments.
"""

import os
import time
import json
import tempfile
from typing import Dict, Optional, Tuple, Any, List
import boto3  # type: ignore
from botocore.exceptions import ClientError, NoCredentialsError  # type: ignore
from python_terraform import Terraform  # type: ignore
from dotenv import load_dotenv
from logger.log_wrapper import get_logger

load_dotenv(override=True)

logger = get_logger("env:aws_fargate", __name__)


def _setup_aws_credentials(is_integration_test: bool) -> None:
    """
    Set up AWS credentials based on is_integration_test flag.
    
    Args:
        is_integration_test: If True, loads TEST_AWS_* credentials and sets them as AWS_* env vars.
                           Otherwise, ensures AWS_* credentials are properly set.
    """
    if is_integration_test:
        # Load test credentials
        test_access_key = os.getenv('TEST_AWS_ACCESS_KEY_ID')
        test_secret_key = os.getenv('TEST_AWS_SECRET_ACCESS_KEY')
        test_region = os.getenv('TEST_AWS_DEFAULT_REGION')
        
        if test_access_key and test_secret_key and test_region:
            # Set standard AWS environment variables for test account
            os.environ['AWS_ACCESS_KEY_ID'] = test_access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = test_secret_key
            os.environ['AWS_DEFAULT_REGION'] = test_region
        else:
            raise ValueError("Test AWS credentials not found. Please configure TEST_AWS_* environment variables.")
    else:
        # Verify sandbox credentials are present
        if not (os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY') and os.getenv('AWS_DEFAULT_REGION')):
            raise ValueError("AWS credentials not found. Please configure AWS_* environment variables.")


def validate_region_consistency() -> None:
    """
    Validate that AWS region configuration is consistent.
    
    Raises:
        ValueError: If region configuration is inconsistent
    """
    aws_region = os.getenv('AWS_DEFAULT_REGION')
    test_region = os.getenv('TEST_AWS_DEFAULT_REGION')
    
    if aws_region and test_region and aws_region != test_region:
        raise ValueError(f"AWS region mismatch: AWS_DEFAULT_REGION={aws_region}, TEST_AWS_DEFAULT_REGION={test_region}")


def get_aws_config(is_integration_test: bool) -> str:
    """
    Get AWS configuration for the specified environment.
    
    Args:
        is_integration_test: If True, uses test account configuration
        
    Returns:
        str: AWS region
    """
    _setup_aws_credentials(is_integration_test)
    
    if is_integration_test:
        return os.getenv('TEST_AWS_DEFAULT_REGION', 'us-east-1')
    else:
        return os.getenv('AWS_DEFAULT_REGION', 'us-east-1')


def get_environment_config(is_integration_test: bool) -> Tuple[str, str]:
    """
    Get environment configuration based on is_integration_test flag.
    
    Args:
        is_integration_test: Flag indicating if this is an integration test environment
        
    Returns:
        Tuple[str, str]: (account_environment, terraform_directory)
        
    Returns:
        - ('test', 'terraform') for integration tests
        - ('sandbox', 'terraform') for production/sandbox
    """
    account_environment = "test" if is_integration_test else "sandbox"
    terraform_directory = "terraform"  # Consolidated terraform directory
    
    return account_environment, terraform_directory


class AWSFargateAgentEnvironment:
    """
    AWS Fargate Agent Environment for managing ECS deployments.
    Uses terraform workspaces to separate test vs sandbox account environments.
    """

    def __init__(self, is_integration_test: bool = False):
        """
        Initialize AWS Fargate Agent Environment.
        
        Args:
            is_integration_test: If True, uses test account credentials and configuration.
                               If False, uses sandbox account credentials and configuration.
        """
        self.is_integration_test = is_integration_test
        
        # Validate region consistency before proceeding
        validate_region_consistency()
        
        # Get AWS region from environment configuration
        self.aws_region = get_aws_config(is_integration_test)
        
        # Get environment configuration - simplified with single terraform directory
        self.account_environment, self.terraform_directory = get_environment_config(is_integration_test)
        
        logger.info(f"AWS Fargate Agent Environment initialized - Account Environment: {self.account_environment} - Region: {self.aws_region} - Terraform Directory: {self.terraform_directory}")
        
        # App environments within ECS Fargate (dev/test/prod)
        self.fargate_app_environments = ['dev', 'test', 'prod']
        
        # Enable verbose terraform logging for debugging
        os.environ['TF_LOG'] = 'INFO'
        
        # Initialize AWS session with appropriate credentials
        self.session = self._create_aws_session()
        
        # Initialize Terraform with consolidated directory
        terraform_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.terraform_directory)
        self.terraform = Terraform(working_dir=terraform_dir)
        
        # Initialize AWS clients
        try:
            self.ecs_client = self.session.client('ecs')
            self.ecr_client = self.session.client('ecr')
            self.logs_client = self.session.client('logs')
            self.elbv2_client = self.session.client('elbv2')
            logger.info(f"AWS clients initialized successfully for account_environment: {self.account_environment}")
        except NoCredentialsError:
            logger.error(f"AWS credentials not found for account_environment: {self.account_environment}")
            raise
        
        # Perform initial infrastructure validation
        self._validate_initial_setup()
    
    def _validate_initial_setup(self) -> None:
        """
        Validate initial setup and provide helpful error messages.
        
        This method checks for common configuration issues and provides
        clear guidance on how to resolve them.
        """
        try:
            # Check AWS credentials are working
            caller_identity = self.session.client('sts').get_caller_identity()
            logger.info(f"AWS credentials validated for account_environment: {self.account_environment}, account: {caller_identity.get('Account', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"AWS credentials validation failed for account_environment: {self.account_environment} - {e}")
            logger.info(f"Please check your AWS credentials configuration in .env file for account_environment: {self.account_environment}")
            raise
        
        # Check if basic infrastructure exists
        readiness_result = self.verify_aws_readiness()
        if not readiness_result:
            logger.warning(f"AWS infrastructure not ready for account_environment: {self.account_environment} in region {self.aws_region}")
            logger.info(f"Run 'python setup.py' to deploy terraform infrastructure or check if infrastructure exists in a different region for account_environment: {self.account_environment}")
    
    def reset(self, app_environment: Optional[str] = None) -> None:
        """
        Clean AWS Fargate deployments by:
        1. Ensuring AWS account is ready for deploy
        2. Stopping and removing existing Fargate services
        3. Removing Docker images from ECR
        
        Args:
            app_environment: Specific app environment to clean ('dev', 'test', 'prod') or None for all
            
        Raises:
            Exception: If any cleaning operation fails
        """
        logger.info(f"Starting AWS Fargate cleanup for account_environment: {self.account_environment}")
        
        app_environments_to_clean = [app_environment] if app_environment else self.fargate_app_environments
        
        for app_env in app_environments_to_clean:
            if app_env not in self.fargate_app_environments:
                raise ValueError(f"Invalid app environment: {app_env}. Valid options: {self.fargate_app_environments}")
                
            logger.info(f"Cleaning Fargate app_environment: {app_env} for account_environment: {self.account_environment}")
            
            # Clean ECS services and tasks
            if not self._clean_ecs_app_environment(app_env):
                raise Exception(f"Failed to clean ECS app_environment: {app_env} for account_environment: {self.account_environment}")
        
        # Clean ECR images (shared across app environments)
        if not self._clean_ecr_images():
            raise Exception(f"Failed to clean ECR images for account_environment: {self.account_environment}")
        
        # Clean old task definitions
        for app_env in self.fargate_app_environments:
            if not self._clean_task_definitions(app_env):
                raise Exception(f"Failed to clean task definitions for app_environment: {app_env} for account_environment: {self.account_environment}")
        
        # Verify AWS account readiness
        if not self.verify_aws_readiness():
            raise Exception(f"AWS account verification failed for account_environment: {self.account_environment}")
        
        logger.info(f"AWS Fargate cleanup completed successfully for account_environment: {self.account_environment}!")
    
    def deploy_image(self, image_tag: str, app_environment: str = 'dev') -> bool:
        """
        Deploy a Docker image to AWS Fargate.
        
        Args:
            image_tag: Docker image tag to deploy
            app_environment: Target app environment ('dev', 'test', 'prod')
            
        Returns:
            bool: True if deployment successful, False otherwise
        """
        if app_environment not in self.fargate_app_environments:
            logger.error(f"Invalid app_environment: {app_environment}. Valid options: {self.fargate_app_environments} for account_environment: {self.account_environment}")
            return False
        
        try:
            logger.info(f"Starting deployment of {image_tag} to app_environment: {app_environment} for account_environment: {self.account_environment}")
            
            # Get ECR repository URL
            repo_url = self._get_ecr_repository_url()
            if not repo_url:
                logger.error(f"ECR repository not found for account_environment: {self.account_environment}")
                return False
            
            # Full image URL
            full_image_url = f"{repo_url}:{image_tag}"
            
            # Get service and cluster names (preserving existing naming convention)
            cluster_name = f"{self.account_environment}-{app_environment}"
            service_name = f"{self.account_environment}-{app_environment}-service"
            
            # Get current task definition
            current_task_def = self._get_current_task_definition(cluster_name, service_name)
            if not current_task_def:
                logger.error(f"Task definition not found for {service_name} in account_environment: {self.account_environment}")
                return False
            
            # Create updated task definition with new image
            new_task_def = self._create_updated_task_definition(current_task_def, full_image_url)
            if not new_task_def:
                logger.error(f"Failed to create updated task definition for account_environment: {self.account_environment}")
                return False
            
            # Update ECS service
            if not self._update_ecs_service(cluster_name, service_name, new_task_def):
                logger.error(f"Failed to update ECS service for account_environment: {self.account_environment}")
                return False
            
            # Wait for deployment to complete
            if not self._wait_for_deployment(cluster_name, service_name):
                logger.error(f"Deployment to app_environment: {app_environment} did not complete successfully for account_environment: {self.account_environment}")
                return False
            
            logger.info(f"Successfully deployed {image_tag} to app_environment: {app_environment} for account_environment: {self.account_environment}")
            return True
            
        except Exception as e:
            logger.error(f"Error during deployment to app_environment: {app_environment} for account_environment: {self.account_environment} - {str(e)}")
            return False
    
    def get_deployment_status(self, app_environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Get deployment status for specified app environment(s).
        
        Args:
            app_environment: Specific app environment to check or None for all
            
        Returns:
            Dict containing deployment status information
        """
        app_environments_to_check = [app_environment] if app_environment else self.fargate_app_environments
        status = {}
        
        for app_env in app_environments_to_check:
            if app_env not in self.fargate_app_environments:
                continue
                
            cluster_name = f"{self.account_environment}-{app_env}"
            service_name = f"{self.account_environment}-{app_env}-service"
            
            try:
                # Get service status
                response = self.ecs_client.describe_services(
                    cluster=cluster_name,
                    services=[service_name]
                )
                
                if response['services']:
                    service = response['services'][0]
                    status[app_env] = {
                        'status': service['status'],
                        'running_count': service['runningCount'],
                        'pending_count': service['pendingCount'],
                        'desired_count': service['desiredCount'],
                        'task_definition': service['taskDefinition'],
                        'platform_version': service.get('platformVersion', 'N/A'),
                        'created_at': service.get('createdAt', 'N/A'),
                        'updated_at': service.get('updatedAt', 'N/A')
                    }
                else:
                    status[app_env] = {'status': 'NOT_FOUND'}
                    
            except ClientError as e:
                status[app_env] = {'status': 'ERROR', 'error': str(e)}
        
        return status
    
    def _create_aws_session(self) -> boto3.Session:
        """
        Create AWS session with appropriate credentials based on environment.
        
        Returns:
            boto3.Session: Configured AWS session
        """
        if self.is_integration_test:
            # Use test account credentials
            access_key = os.getenv('TEST_AWS_ACCESS_KEY_ID')
            secret_key = os.getenv('TEST_AWS_SECRET_ACCESS_KEY')
            region = os.getenv('TEST_AWS_DEFAULT_REGION', self.aws_region)
            
            if access_key and secret_key:
                logger.info(f"Using TEST AWS credentials for {self.account_environment} account environment")
                return boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                logger.warning(f"TEST AWS credentials not found, using default credentials")
        else:
            # Use sandbox/production account credentials
            access_key = os.getenv('AWS_ACCESS_KEY_ID')
            secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            region = os.getenv('AWS_DEFAULT_REGION', self.aws_region)
            
            if access_key and secret_key:
                logger.info(f"Using AWS credentials for {self.account_environment} account environment")
                return boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                logger.warning(f"AWS credentials not found, using default credentials")
        
        # Fallback to default session
        logger.info(f"Using default AWS session for {self.account_environment} account environment")
        return boto3.Session(region_name=self.aws_region)

    def select_workspace(self, workspace_name: str) -> bool:
        """
        Select or create terraform workspace.
        
        Args:
            workspace_name: Name of the workspace to select (test or sandbox)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate workspace name
            if workspace_name not in ['test', 'sandbox']:
                logger.error(f"Invalid workspace name: {workspace_name}. Must be 'test' or 'sandbox'")
                return False
            
            # Try to select workspace
            return_code, stdout, stderr = self.terraform.cmd('workspace', 'select', workspace_name)
            
            if return_code != 0:
                # Workspace doesn't exist, create it
                logger.info(f"Workspace {workspace_name} doesn't exist, creating it")
                return_code, stdout, stderr = self.terraform.cmd('workspace', 'new', workspace_name)
                if return_code != 0:
                    logger.error(f"Failed to create workspace {workspace_name}: {stderr}")
                    return False
            
            logger.info(f"Selected terraform workspace: {workspace_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error selecting workspace {workspace_name}: {e}")
            return False

    def apply_terraform(self) -> bool:
        """
        Apply Terraform configuration to create AWS infrastructure.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Starting Terraform apply for account_environment: {self.account_environment}")
            
            # Select appropriate workspace
            if not self.select_workspace(self.account_environment):
                logger.error(f"Failed to select workspace for account_environment: {self.account_environment}")
                return False
            
            # Initialize terraform
            logger.info(f"Running terraform init for account_environment: {self.account_environment}")
            return_code, stdout, stderr = self.terraform.init()
            logger.info(f"Terraform init return code: {return_code}")
            logger.info(f"Terraform init stdout: {stdout}")
            if stderr:
                logger.warning(f"Terraform init stderr: {stderr}")
            
            if return_code != 0:
                logger.error(f"Terraform init failed for account_environment: {self.account_environment}")
                return False
            
            # Apply terraform configuration with variables
            logger.info(f"Running terraform apply for account_environment: {self.account_environment}")
            tf_vars = self._get_terraform_vars()
            logger.info(f"Terraform variables: {tf_vars}")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tfvars.json', delete=False) as tf_var_file:
                tf_var_file.write(json.dumps(tf_vars))
                tf_var_file_path = tf_var_file.name
            
            try:
                return_code, stdout, stderr = self.terraform.cmd(
                    'apply',
                    '-auto-approve',
                    '-var-file', tf_var_file_path
                )
                logger.info(f"Terraform apply return code: {return_code}")
                logger.info(f"Terraform apply stdout: {stdout}")
                if stderr:
                    logger.warning(f"Terraform apply stderr: {stderr}")
                
                if return_code == 0:
                    logger.info(f"Terraform apply successful for account_environment: {self.account_environment}")
                    return True
                else:
                    logger.error(f"Terraform apply failed for account_environment: {self.account_environment}")
                    return False
            finally:
                # Clean up temporary file
                os.unlink(tf_var_file_path)
        
        except Exception as e:
            logger.error(f"Error during terraform apply for account_environment: {self.account_environment}: {str(e)}")
            return False
    
    def destroy_terraform(self) -> bool:
        """
        Destroy Terraform infrastructure.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Starting Terraform destroy for account_environment: {self.account_environment}")
            
            # Select appropriate workspace
            if not self.select_workspace(self.account_environment):
                logger.error(f"Failed to select workspace for account_environment: {self.account_environment}")
                return False
            
            # Initialize terraform
            logger.info(f"Running terraform init for destroy for account_environment: {self.account_environment}")
            return_code, stdout, stderr = self.terraform.init()
            logger.info(f"Terraform init return code: {return_code}")
            logger.info(f"Terraform init stdout: {stdout}")
            if stderr:
                logger.warning(f"Terraform init stderr: {stderr}")
            
            if return_code != 0:
                logger.error(f"Terraform init failed for destroy for account_environment: {self.account_environment}")
                return False
            
            # Check current state before destroy
            logger.info(f"Checking terraform state before destroy for account_environment: {self.account_environment}")
            return_code, stdout, stderr = self.terraform.cmd('state', 'list')
            logger.info(f"Terraform state list return code: {return_code}")
            logger.info(f"Terraform state list stdout: {stdout}")
            if stderr:
                logger.warning(f"Terraform state list stderr: {stderr}")
            
            if not stdout or stdout.strip() == "":
                logger.info(f"No resources in terraform state for account_environment: {self.account_environment} - nothing to destroy")
                return True
            
            # Destroy terraform with variables
            logger.info(f"Running terraform destroy -auto-approve for account_environment: {self.account_environment}")
            tf_vars = self._get_terraform_vars()
            logger.info(f"Terraform variables: {tf_vars}")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tfvars.json', delete=False) as tf_var_file:
                tf_var_file.write(json.dumps(tf_vars))
                tf_var_file_path = tf_var_file.name
            
            try:
                return_code, stdout, stderr = self.terraform.cmd(
                    'destroy', 
                    '-auto-approve',
                    '-var-file', tf_var_file_path
                )
                logger.info(f"Terraform destroy return code: {return_code}")
                logger.info(f"Terraform destroy stdout: {stdout}")
                if stderr:
                    logger.warning(f"Terraform destroy stderr: {stderr}")
                
                if return_code == 0:
                    logger.info(f"Terraform destroy successful for account_environment: {self.account_environment}")
                    return True
                else:
                    logger.error(f"Terraform destroy failed for account_environment: {self.account_environment}")
                    return False
            finally:
                # Clean up temporary file
                os.unlink(tf_var_file_path)
        
        except Exception as e:
            logger.error(f"Error during terraform destroy for account_environment: {self.account_environment}: {str(e)}")
            return False
    
    def _get_terraform_vars(self) -> Dict[str, Any]:
        """
        Get terraform variables for this account environment.
        
        Returns:
            Dict[str, Any]: Terraform variables
        """
        return {
            'aws_region': self.aws_region,
            'app_environments': self.fargate_app_environments
        }
    
    def _clean_ecs_app_environment(self, app_environment: str) -> bool:
        """Clean ECS resources for a specific app environment."""
        try:
            cluster_name = f"{self.account_environment}-{app_environment}"
            service_name = f"{self.account_environment}-{app_environment}-service"
            
            logger.info(f"Cleaning ECS resources for app_environment: {app_environment}, account_environment: {self.account_environment}")
            
            # First, immediately force-stop all running tasks without waiting for graceful scaling
            logger.info(f"Force stopping all tasks in cluster {cluster_name} for account_environment: {self.account_environment}")
            if not self._force_stop_all_tasks(cluster_name):
                logger.warning(f"Could not force-stop all tasks for account_environment: {self.account_environment}")
            
            # Then update service to 0 desired count (with reduced timeout)
            logger.info(f"Scaling down service {service_name} to 0 tasks for account_environment: {self.account_environment}")
            try:
                self.ecs_client.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    desiredCount=0
                )
                
                # Wait for service to scale down, but with much shorter timeout
                logger.info(f"Waiting briefly for service to scale down for account_environment: {self.account_environment}")
                self._wait_for_service_stable(cluster_name, service_name, timeout=60)
                
            except ClientError as e:
                if 'ServiceNotFoundException' in str(e):
                    logger.info(f"Service {service_name} not found for account_environment: {self.account_environment}, skipping")
                else:
                    logger.error(f"Error scaling down service for account_environment: {self.account_environment}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning ECS app_environment: {app_environment} for account_environment: {self.account_environment}: {str(e)}")
            return False
    
    def _force_stop_all_tasks(self, cluster_name: str) -> bool:
        """Force stop all tasks in a cluster."""
        try:
            # List all tasks in the cluster
            response = self.ecs_client.list_tasks(cluster=cluster_name)
            task_arns = response['taskArns']
            
            if not task_arns:
                logger.info(f"No tasks found in cluster {cluster_name}")
                return True
            
            # Stop all tasks
            for task_arn in task_arns:
                try:
                    self.ecs_client.stop_task(
                        cluster=cluster_name,
                        task=task_arn,
                        reason='Force cleanup'
                    )
                    logger.info(f"Stopped task {task_arn}")
                except ClientError as e:
                    logger.warning(f"Could not stop task {task_arn}: {e}")
            
            return True
            
        except ClientError as e:
            if 'ClusterNotFoundException' in str(e):
                logger.info(f"Cluster {cluster_name} not found, skipping task cleanup")
                return True
            else:
                logger.error(f"Error force stopping tasks: {e}")
                return False
    
    def _clean_ecr_images(self) -> bool:
        """Clean ECR images."""
        try:
            repo_name = f"{self.account_environment}-ecr"
            
            logger.info(f"Cleaning ECR images for account_environment: {self.account_environment}, repository: {repo_name}")
            
            # List images in the repository
            try:
                response = self.ecr_client.describe_images(repositoryName=repo_name)
                images = response['imageDetails']
                
                if not images:
                    logger.info(f"No images found in ECR repository {repo_name}")
                    return True
                
                # Delete all images
                image_ids = []
                for image in images:
                    if 'imageDigest' in image:
                        image_ids.append({'imageDigest': image['imageDigest']})
                
                if image_ids:
                    self.ecr_client.batch_delete_image(
                        repositoryName=repo_name,
                        imageIds=image_ids
                    )
                    logger.info(f"Deleted {len(image_ids)} images from ECR repository {repo_name}")
                
                return True
                
            except ClientError as e:
                if 'RepositoryNotFoundException' in str(e):
                    logger.info(f"ECR repository {repo_name} not found, skipping image cleanup")
                    return True
                else:
                    logger.error(f"Error cleaning ECR images: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error cleaning ECR images for account_environment: {self.account_environment}: {str(e)}")
            return False

    def _clean_task_definitions(self, app_environment: str) -> bool:
        """Clean all task definition revisions for a specific app environment."""
        try:
            task_family = f"{self.account_environment}-{app_environment}"
            
            logger.info(f"Cleaning all task definitions for family: {task_family} in account_environment: {self.account_environment}")
            
            # List all task definitions for the family
            try:
                response = self.ecs_client.list_task_definitions(
                    familyPrefix=task_family,
                    status='ACTIVE'
                )
                
                task_def_arns = response['taskDefinitionArns']
                
                if not task_def_arns:
                    logger.info(f"No task definitions found for family {task_family}")
                    return True
                
                # Deregister all task definitions (no tasks should be running due to prior scale down)
                for task_def_arn in task_def_arns:
                    try:
                        self.ecs_client.deregister_task_definition(
                            taskDefinition=task_def_arn
                        )
                        revision_num = task_def_arn.split(':')[-1]
                        logger.info(f"Deregistered task definition revision {revision_num}: {task_def_arn}")
                    except ClientError as e:
                        revision_num = task_def_arn.split(':')[-1]
                        logger.warning(f"Could not deregister task definition revision {revision_num}: {e}")
                
                logger.info(f"Cleaned {len(task_def_arns)} task definition revisions for family {task_family}")
                return True
                
            except ClientError as e:
                logger.error(f"Error listing task definitions for family {task_family}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error cleaning task definitions for app_environment: {app_environment} in account_environment: {self.account_environment}: {str(e)}")
            return False
    
    def verify_aws_readiness(self) -> bool:
        """Verify AWS account is ready for deployment."""
        try:
            logger.info(f"Verifying AWS account readiness for account_environment: {self.account_environment}")
            
            # Check AWS credentials
            try:
                identity = self.session.client('sts').get_caller_identity()
                account_id = identity.get('Account', 'Unknown')
                logger.info(f"AWS credentials are valid for account_environment: {self.account_environment}, account: {account_id}")
            except Exception as e:
                logger.error(f"AWS credentials are invalid for account_environment: {self.account_environment}: {e}")
                return False
            
            # Check if ECR repository exists
            repo_name = f"{self.account_environment}-ecr"
            try:
                response = self.ecr_client.describe_repositories(repositoryNames=[repo_name])
                repo_uri = response['repositories'][0]['repositoryUri']
                logger.info(f"ECR repository {repo_name} exists for account_environment: {self.account_environment}: {repo_uri}")
            except ClientError as e:
                if 'RepositoryNotFoundException' in str(e):
                    logger.warning(f"ECR repository {repo_name} not found for account_environment: {self.account_environment} in region {self.aws_region}")
                    logger.info(f"Run terraform apply to create infrastructure or check if infrastructure exists in a different region for account_environment: {self.account_environment}")
                    return False
                else:
                    logger.error(f"Error checking ECR repository for account_environment: {self.account_environment}: {e}")
                    return False
            
            # Check if ECS clusters exist
            for app_env in self.fargate_app_environments:
                cluster_name = f"{self.account_environment}-{app_env}"
                try:
                    response = self.ecs_client.describe_clusters(clusters=[cluster_name])
                    if response['clusters'] and response['clusters'][0]['status'] == 'ACTIVE':
                        logger.info(f"ECS cluster {cluster_name} is active for account_environment: {self.account_environment}")
                    else:
                        logger.warning(f"ECS cluster {cluster_name} is not active for account_environment: {self.account_environment} in region {self.aws_region}")
                        logger.info(f"Check if infrastructure exists in a different region for account_environment: {self.account_environment}")
                        return False
                except ClientError as e:
                    if 'ClusterNotFoundException' in str(e):
                        logger.warning(f"ECS cluster {cluster_name} not found for account_environment: {self.account_environment} in region {self.aws_region}")
                        logger.info(f"Run terraform apply to create infrastructure or check if infrastructure exists in a different region for account_environment: {self.account_environment}")
                        return False
                    else:
                        logger.error(f"Error checking ECS cluster {cluster_name} for account_environment: {self.account_environment}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying AWS readiness for account_environment: {self.account_environment}: {str(e)}")
            return False
    
    def _get_ecr_repository_url(self) -> Optional[str]:
        """Get ECR repository URL."""
        try:
            repo_name = f"{self.account_environment}-ecr"
            response = self.ecr_client.describe_repositories(repositoryNames=[repo_name])
            if response['repositories']:
                return response['repositories'][0]['repositoryUri']
            return None
        except ClientError:
            return None
    
    def _get_current_task_definition(self, cluster_name: str, service_name: str) -> Optional[str]:
        """Get current task definition ARN for a service."""
        try:
            response = self.ecs_client.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            if response['services']:
                return response['services'][0]['taskDefinition']
            return None
        except ClientError:
            return None
    
    def _create_updated_task_definition(self, current_task_def_arn: str, new_image: str) -> Optional[str]:
        """Create a new task definition with updated image."""
        try:
            # Get current task definition
            response = self.ecs_client.describe_task_definition(taskDefinition=current_task_def_arn)
            task_def = response['taskDefinition']
            
            # Update image in container definitions
            container_definitions = task_def['containerDefinitions']
            for container in container_definitions:
                container['image'] = new_image
            
            # Register new task definition
            new_task_def = {
                'family': task_def['family'],
                'networkMode': task_def['networkMode'],
                'requiresCompatibilities': task_def['requiresCompatibilities'],
                'cpu': task_def['cpu'],
                'memory': task_def['memory'],
                'executionRoleArn': task_def['executionRoleArn'],
                'taskRoleArn': task_def.get('taskRoleArn'),
                'containerDefinitions': container_definitions
            }
            
            response = self.ecs_client.register_task_definition(**new_task_def)
            return response['taskDefinition']['taskDefinitionArn']
            
        except ClientError as e:
            logger.error(f"Error creating updated task definition: {e}")
            return None
    
    def _update_ecs_service(self, cluster_name: str, service_name: str, task_definition_arn: str) -> bool:
        """Update ECS service with new task definition."""
        try:
            self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=task_definition_arn
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating ECS service: {e}")
            return False
    
    def _wait_for_deployment(self, cluster_name: str, service_name: str, timeout: int = 600) -> bool:
        """Wait for ECS service deployment to complete."""
        try:
            logger.info(f"Waiting for deployment to complete (timeout: {timeout}s)")
            
            waiter = self.ecs_client.get_waiter('services_stable')
            waiter.wait(
                cluster=cluster_name,
                services=[service_name],
                WaiterConfig={'maxAttempts': timeout // 15, 'delay': 15}
            )
            return True
            
        except Exception as e:
            logger.error(f"Deployment did not complete within timeout: {e}")
            return False
    
    def _wait_for_service_stable(self, cluster_name: str, service_name: str, timeout: int = 300) -> bool:
        """Wait for ECS service to become stable."""
        try:
            waiter = self.ecs_client.get_waiter('services_stable')
            waiter.wait(
                cluster=cluster_name,
                services=[service_name],
                WaiterConfig={'maxAttempts': timeout // 15, 'delay': 15}
            )
            return True
        except Exception:
            return False


 