"""
Integration Tests for Docker Tools

Integration tests that require real Docker installation and fail if prerequisites are missing.
All tests run in isolated system temp directories outside the repository.
"""

import unittest
import os
import tempfile
import shutil
import subprocess
from tools.docker_tools import get_tools
from agent_environment.aws_fargate_agent_environment import AWSFargateAgentEnvironment
from tools.context import ToolsContext


def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True
    )


class TestDockerToolsIntegration(unittest.TestCase):
    """Integration tests for Docker tools that require real Docker installation."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_docker_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        tools = get_tools(make_tools_context(self.temp_dir))
        
        class Self:
            def __init__(self, tools):
                self.docker_build_image = tools[0]
                self.docker_build_push_deploy = tools[1]
                self.docker_get_deployment_status = tools[2]
        
        self.docker_tools = Self(tools)
        
        # Ensure Docker is available - fail if not found
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"Docker not found. This is a required prerequisite for integration tests: {e}")
        
        # Ensure AWS CLI is available for ECR operations - fail if not found
        try:
            result = subprocess.run(["aws", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"AWS CLI not found. This is a required prerequisite for integration tests: {e}")
        
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["TEST_AWS_DEFAULT_REGION", "TEST_AWS_ACCESS_KEY_ID", "TEST_AWS_SECRET_ACCESS_KEY"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        self.test_dockerfile_content = """
FROM nginx:alpine
COPY . /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""
        
        # Create a test Dockerfile
        self.dockerfile_path = os.path.join(self.temp_dir, "Dockerfile")
        with open(self.dockerfile_path, 'w') as f:
            f.write(self.test_dockerfile_content)
        
        # Create a simple test file to copy
        test_file = os.path.join(self.temp_dir, "index.html")
        with open(test_file, 'w') as f:
            f.write("<html><body>Integration Test</body></html>")

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_docker_build_image_real_integration(self):
        """Test Docker image build with real Docker - integration test."""
        result = self.docker_tools.docker_build_image(image_tag="integration-test")
        
        # Should succeed
        self.assertTrue(result["success"])

    def test_docker_build_image_without_dockerfile_integration(self):
        """Test Docker build without Dockerfile - should fail appropriately."""
        # Remove Dockerfile
        os.remove(self.dockerfile_path)
        
        result = self.docker_tools.docker_build_image(image_tag="no-dockerfile-test")
        
        # Should fail with Dockerfile not found error
        self.assertFalse(result["success"])
        self.assertTrue(
            "Dockerfile" in result["message"] or
            "not found" in result["message"].lower() or
            "no such file" in result["message"].lower()
        )

    # Removed direct push-to-ECR test; push is now private and covered via build-push-deploy

    def test_build_push_deploy_to_dev_real_integration(self):
        """End-to-end build, push, and deploy to dev - integration test."""
        result = self.docker_tools.docker_build_push_deploy(
            image_name="integration-test",
            image_tag="latest",
            app_environment="dev"
        )
        self.assertIn("Successfully built, pushed, and deployed image", result.get("message", ""))
        if result.get("success"):
            self.assertTrue("load_balancer_url" in result and result["load_balancer_url"].startswith("http"))

    def test_build_push_deploy_to_test_real_integration(self):
        """End-to-end build, push, and deploy to test - integration test."""
        result = self.docker_tools.docker_build_push_deploy(
            image_name="integration-test",
            image_tag="latest",
            app_environment="test"
        )
        self.assertIn("Successfully built, pushed, and deployed image", result.get("message", ""))
        if result.get("success"):
            self.assertTrue("load_balancer_url" in result and result["load_balancer_url"].startswith("http"))

    def test_build_push_deploy_to_prod_real_integration(self):
        """End-to-end build, push, and deploy to prod - integration test."""
        result = self.docker_tools.docker_build_push_deploy(
            image_name="integration-test",
            image_tag="latest",
            app_environment="prod"
        )
        self.assertIn("Successfully built, pushed, and deployed image", result.get("message", ""))
        if result.get("success"):
            self.assertTrue("load_balancer_url" in result and result["load_balancer_url"].startswith("http"))

    def test_docker_build_push_deploy_real_integration(self):
        """Test complete Docker workflow with real systems - integration test."""
        result = self.docker_tools.docker_build_push_deploy(
            image_name="integration-workflow-test",
            image_tag="latest",
            app_environment="dev"
        )
        
        # Should successfully complete workflow
        self.assertIn("Successfully built, pushed, and deployed image", result.get("message", ""))
        # Should return the effective unique tag (not 'latest')
        self.assertIn("effective_image_tag", result)
        self.assertNotEqual(result.get("effective_image_tag"), "latest")
        # Should include load balancer URL on success
        if result.get("success"):
            self.assertTrue("load_balancer_url" in result and result["load_balancer_url"].startswith("http"))

    def test_docker_build_push_deploy_to_test_real_integration(self):
        """Test complete Docker workflow to test environment with real systems - integration test."""
        result = self.docker_tools.docker_build_push_deploy(
            image_name="integration-workflow-test",
            image_tag="latest",
            app_environment="test"
        )
        
        # Should successfully complete workflow
        self.assertIn("Successfully built, pushed, and deployed image", result.get("message", ""))
        self.assertIn("test", result.get("message", "").lower())
        # Should return the effective unique tag (not 'latest')
        self.assertIn("effective_image_tag", result)
        self.assertNotEqual(result.get("effective_image_tag"), "latest")

    def test_docker_get_deployment_status_real_integration(self):
        """Test getting deployment status with real AWS - integration test."""
        result = self.docker_tools.docker_get_deployment_status("test")
        
        # Should get successful deployment status
        self.assertTrue(
            "Deployment Status" in result or
            "Service" in result
        )

    # Removed direct deploy failure diagnostics test; public deploy API removed


class TestDockerToolsErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling in Docker tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_docker_error_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        tools = get_tools(make_tools_context(self.temp_dir))
        
        class Self:
            def __init__(self, tools):
                self.docker_build_image = tools[0]
                self.docker_build_push_deploy = tools[1]
                self.docker_get_deployment_status = tools[2]
        
        self.docker_tools = Self(tools)
        
        # Ensure Docker is available - fail if not found
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"Docker not found. This is a required prerequisite for integration tests: {e}")

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_docker_build_invalid_dockerfile_integration(self):
        """Test Docker build with invalid Dockerfile - should fail appropriately."""
        # Create invalid Dockerfile
        dockerfile_path = os.path.join(self.temp_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write("INVALID_INSTRUCTION nginx:alpine\n")
        
        result = self.docker_tools.docker_build_image(image_tag="invalid-test")
        
        # Should fail with Docker syntax error
        self.assertFalse(result["success"])
        self.assertTrue(
            "Error" in result["message"] or
            "build failed" in result["message"].lower() or
            "docker" in result["message"].lower()
        )

    def test_docker_operations_without_permissions_integration(self):
        """Test Docker operations that require permissions - integration test."""
        # Create a test Dockerfile first
        dockerfile_path = os.path.join(self.temp_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write("FROM nginx:alpine\nCOPY . /usr/share/nginx/html/\nEXPOSE 80\n")
        
        # Create a simple test file to copy
        test_file = os.path.join(self.temp_dir, "index.html")
        with open(test_file, 'w') as f:
            f.write("<html><body>Test</body></html>")
        
        # Try to build with a valid tag name
        result = self.docker_tools.docker_build_image(image_name="restricted-test", image_tag="latest")
        
        # Should succeed
        self.assertTrue(result["success"])


class TestDockerToolsAWSIntegration(unittest.TestCase):
    """Integration tests for Docker tools AWS integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_docker_aws_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        tools = get_tools(make_tools_context(self.temp_dir))
        
        class Self:
            def __init__(self, tools):
                self.docker_build_image = tools[0]
                self.docker_build_push_deploy = tools[1]
                self.docker_get_deployment_status = tools[2]
        
        self.docker_tools = Self(tools)
        
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["TEST_AWS_DEFAULT_REGION", "TEST_AWS_ACCESS_KEY_ID", "TEST_AWS_SECRET_ACCESS_KEY"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_aws_fargate_agent_environment_integration(self):
        """Test AWS Fargate agent environment integration."""
        # Create temporary environment for testing
        aws_env = AWSFargateAgentEnvironment(is_integration_test=True)
        
        # This should make real AWS calls and succeed
        result = aws_env.verify_aws_readiness()
        # Should succeed
        self.assertTrue(result, "AWS readiness check should succeed")

    def test_docker_environment_consistency_integration(self):
        """Test Docker and AWS environment consistency integration."""
        # Create a test Dockerfile first
        dockerfile_path = os.path.join(self.temp_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write("FROM nginx:alpine\nCOPY . /usr/share/nginx/html/\nEXPOSE 80\n")
        
        # Create a simple test file to copy
        test_file = os.path.join(self.temp_dir, "index.html")
        with open(test_file, 'w') as f:
            f.write("<html><body>Consistency Test</body></html>")
        
        # Test that Docker tools work with AWS environment
        docker_result = self.docker_tools.docker_build_image(image_tag="consistency-test")
        
        # Should succeed
        self.assertTrue(isinstance(docker_result, dict))
        self.assertTrue(docker_result.get("success"))

    def test_docker_real_aws_calls_integration(self):
        """Test Docker tools making real AWS calls through build-push-deploy."""
        result = self.docker_tools.docker_build_push_deploy(
            image_name="real-aws-test",
            image_tag="integration",
            app_environment="dev"
        )
        # Should indicate success and include image_uri from push
        self.assertTrue(isinstance(result, dict))
        self.assertIn("effective_image_tag", result)
        # image_uri suggests successful ECR interaction
        if result.get("success"):
            self.assertIn("image_uri", result)


if __name__ == '__main__':
    unittest.main() 