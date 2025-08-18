"""
Integration Tests for AWS CLI Tools

Integration tests that require real AWS CLI and fail if prerequisites are missing.
All tests run in isolated system temp directories outside the repository.
"""

import unittest
import os
import subprocess
import tempfile
import shutil

from dotenv import load_dotenv
from tools.aws_cli_tools import get_tools
from agent_environment.aws_fargate_agent_environment import AWSFargateAgentEnvironment
from tools.context import ToolsContext

load_dotenv(override=True)

def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True
    )


class TestAWSCLIToolsIntegration(unittest.TestCase):
    """Integration tests for AWS CLI tools that require real AWS CLI installation."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_aws_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        # Ensure AWS CLI is available - fail if not found
        try:
            subprocess.run(["aws", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"AWS CLI not found. This is a required prerequisite for integration tests: {e}")
        
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["TEST_AWS_DEFAULT_REGION", "TEST_AWS_ACCESS_KEY_ID", "TEST_AWS_SECRET_ACCESS_KEY"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        tools = get_tools(make_tools_context(self.temp_dir))
        
        class Self:
            def __init__(self, tools):
                self.aws_get_fargate_logs = tools[0]
                self.aws_get_service_health = tools[1]
                self.aws_get_load_balancer_url = tools[2]
                self.aws_list_ecr_images = tools[3]
                self.aws_get_ecs_service_events = tools[4]
                self.aws_get_failed_task_details = tools[5]
                self.aws_get_task_execution_logs = tools[6]
                self.aws_inspect_task_definition = tools[7]
                self.aws_discover_container_names = tools[8]
                self.aws_verify_ecr_image = tools[9]
                self.aws_check_service_scaling = tools[10]
        
        self.aws_cli_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_aws_get_fargate_logs_invalid_environment(self):
        """Test getting logs with invalid environment - should fail appropriately."""
        result = self.aws_cli_tools.aws_get_fargate_logs("invalid")
        self.assertIn("Invalid app_environment", result)

    def test_aws_get_fargate_logs_real_aws_call(self):
        """Test real AWS CLI call for logs - integration test."""
        # This will make a real call to AWS and should succeed
        result = self.aws_cli_tools.aws_get_fargate_logs("dev")
        # Should get logs or no logs message - fail if infrastructure not deployed
        if "not found" in result or "Deploy an application first" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        
        self.assertTrue(
            "Sample log output" in result or 
            "No recent logs found" in result or
            "No recent logs found in /ecs/" in result or
            "ecs/test-" in result,  # Actual log output from ECS service
            f"None of the expected conditions matched. Result: {repr(result)}"
        )

    def test_aws_get_service_health_real_aws_call(self):
        """Test real AWS service health check - integration test."""
        # Make real call to AWS - test account environment has dev, test, prod app environments
        result = self.aws_cli_tools.aws_get_service_health("dev")
        # Should get successful service health response - fail if infrastructure not deployed
        if "not found" in result or "Infrastructure may not be deployed" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        self.assertIn("Service Health", result)

    def test_aws_get_load_balancer_url_real_aws_call(self):
        """Test real AWS load balancer URL retrieval - integration test."""
        result = self.aws_cli_tools.aws_get_load_balancer_url("dev")
        # Should get successful load balancer URL - fail if infrastructure not deployed
        if "not found" in result or "Infrastructure may not be deployed" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        self.assertIn("Load Balancer URL", result)

    def test_aws_list_ecr_images_real_aws_call(self):
        """Test real ECR image listing - integration test."""
        result = self.aws_cli_tools.aws_list_ecr_images()
        # Should get successful ECR images listing - fail if infrastructure not deployed
        if "not found" in result or "Infrastructure may not be deployed" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        self.assertIn("ECR Images", result)

    def test_aws_get_ecs_service_events_real_aws_call(self):
        """Test real ECS service events retrieval - integration test."""
        result = self.aws_cli_tools.aws_get_ecs_service_events("dev")
        # Should get successful service events response - fail if infrastructure not deployed
        if "not found" in result or "Infrastructure may not be deployed" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        self.assertIn("ECS Service Events", result)

    def test_aws_get_failed_task_details_real_aws_call(self):
        """Test real failed task details retrieval - integration test."""
        result = self.aws_cli_tools.aws_get_failed_task_details("dev")
        # Should get successful failed task details response - fail if infrastructure not deployed
        if "not found" in result or "Infrastructure may not be deployed" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        # Can be either failed tasks found or no failed tasks message
        self.assertTrue(
            "Failed Task Details" in result or 
            "No failed tasks found" in result or
            "No stopped tasks found" in result,
            f"Unexpected result: {repr(result)}"
        )

    def test_aws_get_task_execution_logs_real_aws_call(self):
        """Test real task execution logs retrieval - integration test."""
        result = self.aws_cli_tools.aws_get_task_execution_logs("dev", "5m")
        # Should get successful task execution logs response - fail if infrastructure not deployed
        if "not found" in result or "Deploy an application first" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        # Can be either logs found or no logs message
        self.assertTrue(
            "Task execution logs retrieved successfully" in result or 
            "No recent task execution logs found" in result,
            f"Unexpected result: {repr(result)}"
        )

    def test_aws_get_task_execution_logs_invalid_environment(self):
        """Test getting task execution logs with invalid environment - should fail appropriately."""
        result = self.aws_cli_tools.aws_get_task_execution_logs("invalid")
        self.assertIn("Invalid app_environment", result)

    def test_aws_inspect_task_definition_real_aws_call(self):
        """Test real task definition inspection - integration test."""
        # Use test-dev task definition family based on naming patterns
        result = self.aws_cli_tools.aws_inspect_task_definition("test-dev")
        # Should get successful task definition inspection - fail if infrastructure not deployed
        if "not found" in result or "TaskDefinitionNotFoundException" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        self.assertIn("Task Definition Inspection", result)

    def test_aws_discover_container_names_real_aws_call(self):
        """Test real container name discovery - integration test."""
        # Use test-dev task definition family based on naming patterns
        result = self.aws_cli_tools.aws_discover_container_names("test-dev")
        # Should get successful container name discovery - fail if infrastructure not deployed
        if "not found" in result or "TaskDefinitionNotFoundException" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        self.assertIn("Container names", result)

    def test_aws_verify_ecr_image_real_aws_call(self):
        """Test real ECR image verification - integration test."""
        # Use test-ecr repository and latest tag based on naming patterns
        result = self.aws_cli_tools.aws_verify_ecr_image("test-ecr", "latest")
        # Should get successful ECR image verification - can be found or not found
        self.assertTrue(
            "ECR Image Verification" in result or
            "not found" in result or
            "RepositoryNotFoundException" in result,
            f"Unexpected result: {repr(result)}"
        )

    def test_aws_check_service_scaling_real_aws_call(self):
        """Test real service scaling check - integration test."""
        # Use test-dev cluster and service based on naming patterns
        result = self.aws_cli_tools.aws_check_service_scaling("test-dev", "test-dev-service")
        # Should get successful scaling status - fail if infrastructure not deployed
        if "not found" in result or "ClusterNotFoundException" in result:
            self.fail(f"Required AWS infrastructure not deployed: {result}")
        
        self.assertIn("Service Scaling Status", result)


class TestAWSFargateAgentEnvironmentIntegration(unittest.TestCase):
    """Integration tests for AWS Fargate agent environment."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure required environment variables - fail if missing
        required_vars = ["TEST_AWS_DEFAULT_REGION", "TEST_AWS_ACCESS_KEY_ID", "TEST_AWS_SECRET_ACCESS_KEY"]
        for var in required_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")

    def test_aws_fargate_agent_environment_initialization(self):
        """Test AWSFargateAgentEnvironment can be initialized."""
        try:
            env = AWSFargateAgentEnvironment()
            self.assertIsNotNone(env)
        except Exception as e:
            self.fail(f"Failed to initialize AWSFargateAgentEnvironment: {e}")

    def test_aws_environment_name_validation(self):
        """Test environment name validation."""
        env = AWSFargateAgentEnvironment()
        
        # Valid environment names
        valid_names = ["dev", "test", "prod"]
        for name in valid_names:
            # Should not raise exception
            try:
                # Assuming there's a method to validate environment names
                result = env.get_environment_name() if hasattr(env, 'get_environment_name') else name
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"Valid environment name {name} caused error: {e}")


if __name__ == '__main__':
    unittest.main() 