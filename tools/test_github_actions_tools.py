"""
Integration Tests for GitHub Actions Tools

Integration tests that require real GitHub CLI and environment variables. 
All tests run in isolated system temp directories outside the repository.
No mocks are used - tests must fail if prerequisites are missing.
"""

import unittest
import os
import tempfile
import shutil
import subprocess
from tools.github_actions_tools import get_tools
from tools.context import ToolsContext
from dotenv import load_dotenv

load_dotenv(override=True)


def clone_test_repository(test_dir):
    """Helper function to clone the test repository to the current directory."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set for integration tests")
    
    repo_owner = os.getenv("GITHUB_REPO_OWNER")
    repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
    github_repo = f"{repo_owner}/{repo_name}" if repo_owner and repo_name else None
    if not github_repo:
        raise ValueError("GitHub repository not configured. Check GITHUB_REPO_OWNER and GITHUB_TEST_REPO_NAME environment variables.")
    
    # Use direct git clone with token for private repository access, clone to current directory
    clone_url = f"https://{github_token}@github.com/{github_repo}.git"
    clone_result = subprocess.run(
        ["git", "clone", clone_url, "."], 
        cwd=test_dir, 
        capture_output=True, 
        text=True
    )
    if clone_result.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {clone_result.stderr}")


def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True
    )


class TestGitHubActionsToolsIntegration(unittest.TestCase):
    """Integration tests for GitHub Actions tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.test_dir = tempfile.mkdtemp(prefix="orcagent_gh_actions_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.test_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        # Ensure GitHub CLI is available - fail if not found
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"GitHub CLI not found. This is a required prerequisite for integration tests: {e}")
        
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["GITHUB_TOKEN", "GITHUB_TEST_REPO_NAME", "GITHUB_REPO_OWNER"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        # Clone test repository to the current directory
        try:
            clone_test_repository(self.test_dir)
        except (ValueError, RuntimeError) as e:
            self.fail(f"Failed to set up git repository for Actions tests: {e}")
        
        tools = get_tools(make_tools_context(self.test_dir))
        
        class Self:
            def __init__(self, tools):
                self.gh_actions_list = tools[0]
                self.gh_actions_status = tools[1]
                self.gh_actions_view = tools[2]
                self.gh_actions_logs = tools[3]
                self.gh_actions_rerun = tools[4]
                self.gh_actions_cancel = tools[5]
                self.gh_actions_dispatch = tools[6]
                self.gh_actions_download_artifact = tools[7]
                self.gh_actions_enable_workflow = tools[8]
                self.gh_actions_disable_workflow = tools[9]
                self.gh_actions_wait_for_workflows = tools[10]
                self.gh_actions_list_jobs = tools[11]
                self.gh_actions_job_logs = tools[12]
        
        self.github_actions_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gh_actions_list_real_integration(self):
        """Test listing GitHub Actions workflows with real GitHub CLI."""
        result = self.github_actions_tools.gh_actions_list()
        
        # Should succeed with real GitHub response in proper git repository
        self.assertIn("GitHub Actions workflows:", result)

    def test_gh_actions_status_real_integration(self):
        """Test GitHub Actions status with real GitHub CLI."""
        result = self.github_actions_tools.gh_actions_status()
        
        # Should succeed with real GitHub response in proper git repository
        self.assertIn("GitHub Actions workflow run status:", result)


class TestGitHubActionsToolsErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling in GitHub Actions tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.test_dir = tempfile.mkdtemp(prefix="orcagent_gh_actions_error_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.test_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        # Ensure GitHub CLI is available - fail if not found
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"GitHub CLI not found. This is a required prerequisite for integration tests: {e}")
        
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["GITHUB_TOKEN", "GITHUB_TEST_REPO_NAME", "GITHUB_REPO_OWNER"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        # Clone test repository to the current directory
        try:
            clone_test_repository(self.test_dir)
        except (ValueError, RuntimeError) as e:
            self.fail(f"Failed to set up git repository for Actions error tests: {e}")
        
        tools = get_tools(make_tools_context(self.test_dir))
        
        class Self:
            def __init__(self, tools):
                self.gh_actions_list = tools[0]
                self.gh_actions_status = tools[1]
                self.gh_actions_view = tools[2]
                self.gh_actions_logs = tools[3]
                self.gh_actions_rerun = tools[4]
                self.gh_actions_cancel = tools[5]
                self.gh_actions_dispatch = tools[6]
                self.gh_actions_download_artifact = tools[7]
                self.gh_actions_enable_workflow = tools[8]
                self.gh_actions_disable_workflow = tools[9]
                self.gh_actions_wait_for_workflows = tools[10]
                self.gh_actions_list_jobs = tools[11]
                self.gh_actions_job_logs = tools[12]
        
        self.github_actions_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gh_actions_view_real_integration(self):
        """Test viewing GitHub Actions run with real GitHub CLI."""
        # Try to view a non-existent run ID to test error handling
        result = self.github_actions_tools.gh_actions_view("99999")
        
        # Should get specific error for non-existent run
        self.assertIn("not found", result.lower())

    def test_gh_actions_logs_real_integration(self):
        """Test getting GitHub Actions logs with real GitHub CLI."""
        # Try to get logs for non-existent run
        result = self.github_actions_tools.gh_actions_logs("99999")
        
        # Should get specific error for non-existent run
        self.assertIn("not found", result.lower())

    def test_gh_actions_rerun_real_integration(self):
        """Test rerunning GitHub Actions with real GitHub CLI."""
        # Try to rerun non-existent run
        result = self.github_actions_tools.gh_actions_rerun("99999")
        
        # Should get specific error for non-existent run
        self.assertIn("not found", result.lower())

    def test_gh_actions_cancel_real_integration(self):
        """Test canceling GitHub Actions with real GitHub CLI."""
        # Try to cancel non-existent run
        result = self.github_actions_tools.gh_actions_cancel("99999")
        
        # Should get specific error for non-existent run
        self.assertIn("could not find any workflow run", result.lower())

    def test_gh_actions_dispatch_real_integration(self):
        """Test dispatching GitHub Actions workflow with real GitHub CLI."""
        # Try to dispatch non-existent workflow
        result = self.github_actions_tools.gh_actions_dispatch("non-existent-workflow")
        
        # Should get specific error for non-existent workflow
        self.assertIn("could not find any workflows", result.lower())

    def test_gh_actions_download_artifact_real_integration(self):
        """Test downloading artifacts with real GitHub CLI."""
        # Try to download from non-existent run
        result = self.github_actions_tools.gh_actions_download_artifact("99999")
        
        # Should get specific error for non-existent run
        self.assertIn("not found", result.lower())

    def test_gh_actions_enable_workflow_real_integration(self):
        """Test enabling workflow with real GitHub CLI."""
        # Try to enable non-existent workflow
        result = self.github_actions_tools.gh_actions_enable_workflow("non-existent-workflow")
        
        # Should get specific error for non-existent workflow
        self.assertIn("could not find any workflows", result.lower())

    def test_gh_actions_disable_workflow_real_integration(self):
        """Test disabling workflow with real GitHub CLI."""
        # Try to disable non-existent workflow
        result = self.github_actions_tools.gh_actions_disable_workflow("non-existent-workflow")
        
        # Should get specific error for non-existent workflow
        self.assertIn("could not find any workflows", result.lower())

    def test_gh_actions_wait_for_workflows_real_integration(self):
        """Test waiting for workflows with real GitHub CLI."""
        # Should either find none active or complete successfully within a short timeout
        result = self.github_actions_tools.gh_actions_wait_for_workflows(timeout_seconds=5, poll_interval_seconds=1)
        self.assertTrue(
            any(
                phrase in result
                for phrase in [
                    "No active GitHub Actions workflow runs found",
                    "All GitHub Actions workflow runs have completed",
                    "Timeout waiting for GitHub Actions workflows to complete",
                ]
            )
        )

    def test_gh_actions_list_jobs_real_integration(self):
        """Test listing jobs for workflow run with real GitHub CLI."""
        # Try to list jobs for non-existent run
        result = self.github_actions_tools.gh_actions_list_jobs("99999")
        
        # Should get a clear error for non-existent run or a structured no-jobs response
        self.assertTrue(
            any(
                phrase in result.lower()
                for phrase in [
                    "not found",
                    "could not find",
                    "no jobs found",
                    "error",
                ]
            )
        )

    def test_gh_actions_job_logs_real_integration(self):
        """Test getting job logs with real GitHub CLI."""
        # Try to get logs for non-existent job
        result = self.github_actions_tools.gh_actions_job_logs("99999", "99999")
        
        # Should get specific error for non-existent job
        self.assertIn("not found", result.lower())


class TestGitHubActionsToolsWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete GitHub Actions workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.test_dir = tempfile.mkdtemp(prefix="orcagent_gh_actions_workflow_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.test_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        # Ensure GitHub CLI is available - fail if not found
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"GitHub CLI not found. This is a required prerequisite for integration tests: {e}")
        
        # Ensure required environment variables - fail if missing
        required_env_vars = ["GITHUB_TOKEN", "GITHUB_TEST_REPO_NAME", "GITHUB_REPO_OWNER"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        # Create GitHub Actions tools instance
        tools = get_tools(make_tools_context(self.test_dir))
        
        class Self:
            def __init__(self, tools):
                self.gh_actions_list = tools[0]
                self.gh_actions_status = tools[1]
                self.gh_actions_view = tools[2]
                self.gh_actions_logs = tools[3]
                self.gh_actions_rerun = tools[4]
                self.gh_actions_cancel = tools[5]
                self.gh_actions_dispatch = tools[6]
                self.gh_actions_download_artifact = tools[7]
                self.gh_actions_enable_workflow = tools[8]
                self.gh_actions_disable_workflow = tools[9]
                self.gh_actions_wait_for_workflows = tools[10]
                self.gh_actions_list_jobs = tools[11]
                self.gh_actions_job_logs = tools[12]
        
        self.github_actions_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gh_authentication_integration(self):
        """Test GitHub CLI authentication for Actions - integration test."""
        try:
            result = subprocess.run(["gh", "auth", "status"], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.test_dir)
            
            # Should be authenticated successfully
            self.assertEqual(result.returncode, 0)
            self.assertIn("Logged in", result.stdout)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"GitHub CLI authentication test failed: {e}")

    def test_gh_repository_actions_access_integration(self):
        """Test GitHub repository Actions access - integration test."""
        repo_owner = os.getenv("GITHUB_REPO_OWNER")
        test_repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
        test_repo = f"{repo_owner}/{test_repo_name}" if repo_owner and test_repo_name else None
        if test_repo:
            try:
                result = subprocess.run(["gh", "api", f"repos/{test_repo}/actions/workflows"], 
                                      capture_output=True, 
                                      text=True,
                                      cwd=self.test_dir)
                
                # Should successfully access repository Actions
                self.assertIn("workflows", result.stdout.lower())
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.fail(f"GitHub Actions access test failed: {e}")

    def test_complete_actions_workflow_investigation_integration(self):
        """Test complete Actions workflow investigation - integration test."""
        # Clone test repository to the current directory
        try:
            clone_test_repository(self.test_dir)
        except (ValueError, RuntimeError) as e:
            self.fail(f"Failed to set up git repository for workflow investigation test: {e}")
        
        # List workflows
        workflows = self.github_actions_tools.gh_actions_list()
        self.assertIsInstance(workflows, str)
        
        # Check status
        status = self.github_actions_tools.gh_actions_status()
        self.assertIsInstance(status, str)
        
        # These should all be successful real responses
        self.assertIn("GitHub Actions", workflows)
        self.assertIn("GitHub Actions", status)


if __name__ == '__main__':
    unittest.main() 