"""
Integration Tests for GitHub PR Tools

Integration tests that require real GitHub CLI and environment variables.
All tests run in isolated system temp directories outside the repository.
No mocks are used - tests must fail if prerequisites are missing.
"""

import unittest
import os
import tempfile
import shutil
import subprocess

from dotenv import load_dotenv
from tools.github_pr_tools import get_tools
from tools.context import ToolsContext

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


class TestGitHubPRToolsIntegration(unittest.TestCase):
    """Integration tests for GitHub PR tools that require real GitHub CLI."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_gh_pr_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
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
            clone_test_repository(self.temp_dir)
        except (ValueError, RuntimeError) as e:
            self.fail(f"Failed to set up git repository for PR tests: {e}")
        
        tools = get_tools(make_tools_context(self.temp_dir))
        
        class Self:
            def __init__(self, tools):
                self.gh_pr_create = tools[0]
                self.gh_pr_list = tools[1]
                self.gh_pr_view = tools[2]
                self.gh_pr_edit = tools[3]
                self.gh_pr_merge = tools[4]
                self.gh_pr_close = tools[5]
                self.gh_pr_reopen = tools[6]
                self.gh_pr_ready = tools[7]
                self.gh_pr_review = tools[8]
                self.gh_pr_status = tools[9]
                self.gh_pr_checks = tools[10]
                self.gh_pr_comment = tools[11]
                self.gh_pr_diff = tools[12]
                self.gh_pr_checkout = tools[13]
        
        self.github_pr_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_gh_pr_create_real_integration(self):
        """Test PR creation with real GitHub CLI - integration test."""
        # Test PR creation on main branch which should give specific error
        result = self.github_pr_tools.gh_pr_create(
            title="Integration Test PR",
            body="This is an integration test PR",
            draft=True,
            reviewers="invalid-user-name-12345",
            assignees="another-bad-user-98765"
        )
        
        # Should get a safe validation error from our wrapper or the gh CLI
        self.assertTrue(
            ("no commits between" in result.lower()) or
            ("must be on a branch named differently" in result)
        )

    def test_gh_pr_create_creates_head_branch_when_absent(self):
        """Creating a PR with a non-existent head should create the branch locally (even if PR is blocked by no commits)."""
        new_branch = "orcagent_test_branch_does_not_exist"

        # Verify branch does not exist before
        before = subprocess.run(["git", "rev-parse", "--verify", f"refs/heads/{new_branch}"], cwd=self.temp_dir, capture_output=True, text=True)
        self.assertNotEqual(before.returncode, 0)

        # Attempt PR create, which should create branch but block due to no commits
        result = self.github_pr_tools.gh_pr_create(
            title="Attempt PR with new head",
            head=new_branch,
            draft=True
        )
        self.assertIn("no commits", result.lower())

        # Verify branch now exists locally
        after = subprocess.run(["git", "rev-parse", "--verify", f"refs/heads/{new_branch}"], cwd=self.temp_dir, capture_output=True, text=True)
        self.assertEqual(after.returncode, 0)

    def test_gh_pr_list_real_integration(self):
        """Test listing PRs with real GitHub CLI - integration test."""
        result = self.github_pr_tools.gh_pr_list()
        
        # Should succeed with real GitHub CLI in proper git repository
        self.assertIn("Pull Requests", result)

    def test_gh_pr_view_real_integration(self):
        """Test viewing PR with real GitHub CLI - integration test."""
        # View current PR or get appropriate no-PR message
        result = self.github_pr_tools.gh_pr_view()
        
        # Should succeed with either PR data or valid no-PR message
        self.assertTrue(
            "no pull request" in result.lower() or
            "#" in result  # Actual PR data would contain PR number
        )

    def test_gh_pr_status_real_integration(self):
        """Test PR status with real GitHub CLI - integration test."""
        result = self.github_pr_tools.gh_pr_status()
        
        # Should succeed with either status data or valid no-PR message
        self.assertTrue(
            "Pull Request Status" in result or
            "no pull request" in result.lower()
        )

    def test_gh_pr_checks_real_integration(self):
        """Test PR checks with real GitHub CLI - integration test."""
        result = self.github_pr_tools.gh_pr_checks()
        
        # Should succeed with either checks data or valid no-PR message
        self.assertTrue(
            "no pull request" in result.lower() or
            "checks" in result.lower()
        )

    def test_gh_pr_diff_real_integration(self):
        """Test PR diff with real GitHub CLI - integration test."""
        result = self.github_pr_tools.gh_pr_diff()
        
        # Should succeed with either diff data or valid no-PR message
        self.assertTrue(
            "no pull request" in result.lower() or
            "diff" in result.lower() or
            "@@" in result  # Diff format marker
        )


class TestGitHubPRToolsErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling in GitHub PR tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_gh_pr_error_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        self.test_repo_dir = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(self.test_repo_dir)
        
        # Ensure GitHub CLI is available - fail if not found
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"GitHub CLI not found. This is a required prerequisite for integration tests: {e}")
        
        # Create GitHub PR tools instance in non-git directory for error testing
        tools = get_tools(make_tools_context(self.test_repo_dir))
        
        class Self:
            def __init__(self, tools):
                self.gh_pr_create = tools[0]
                self.gh_pr_list = tools[1]
                self.gh_pr_view = tools[2]
                self.gh_pr_edit = tools[3]
                self.gh_pr_merge = tools[4]
                self.gh_pr_close = tools[5]
                self.gh_pr_reopen = tools[6]
                self.gh_pr_ready = tools[7]
                self.gh_pr_review = tools[8]
                self.gh_pr_status = tools[9]
                self.gh_pr_checks = tools[10]
                self.gh_pr_comment = tools[11]
                self.gh_pr_diff = tools[12]
                self.gh_pr_checkout = tools[13]
        
        self.github_pr_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_gh_pr_create_without_git_repo_integration(self):
        """Test PR creation without git repository - should fail appropriately."""
        # This directory is not a git repository
        result = self.github_pr_tools.gh_pr_create(
            title="Test PR",
            body="Test description"
        )
        
        # Should fail specifically with git repository error
        self.assertIn("not a git repository", result.lower())

    def test_gh_pr_invalid_operation_integration(self):
        """Test invalid PR operations with real GitHub CLI."""
        # Clone test repository to the current directory
        try:
            clone_test_repository(self.test_repo_dir)
        except (ValueError, RuntimeError) as e:
            self.fail(f"Failed to set up git repository for error test: {e}")
        
        # Try to view non-existent PR in proper git repository
        result = self.github_pr_tools.gh_pr_view("99999")
        
        # Should get specific error for non-existent PR
        self.assertIn("could not resolve to a pullrequest", result.lower())

    def test_gh_comment_empty_body_integration(self):
        """Test commenting with empty body - should fail appropriately."""
        result = self.github_pr_tools.gh_pr_comment(body="")
        
        # Should fail with empty body error
        self.assertIn("Comment body cannot be empty", result)

    def test_gh_merge_invalid_method_integration(self):
        """Test merging with invalid method - should fail appropriately."""
        result = self.github_pr_tools.gh_pr_merge(merge_method="invalid")
        
        # Should fail with invalid method error
        self.assertIn("Invalid merge method", result)


class TestGitHubPRToolsWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete GitHub PR workflows."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_gh_pr_workflow_test_")
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        self.test_repo_dir = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(self.test_repo_dir)
        
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
        
        # Create GitHub PR tools instance
        tools = get_tools(make_tools_context(self.test_repo_dir))
        
        class Self:
            def __init__(self, tools):
                self.gh_pr_create = tools[0]
                self.gh_pr_list = tools[1]
                self.gh_pr_view = tools[2]
                self.gh_pr_edit = tools[3]
                self.gh_pr_merge = tools[4]
                self.gh_pr_close = tools[5]
                self.gh_pr_reopen = tools[6]
                self.gh_pr_ready = tools[7]
                self.gh_pr_review = tools[8]
                self.gh_pr_status = tools[9]
                self.gh_pr_checks = tools[10]
                self.gh_pr_comment = tools[11]
                self.gh_pr_diff = tools[12]
                self.gh_pr_checkout = tools[13]
        
        self.github_pr_tools = Self(tools)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_gh_authentication_integration(self):
        """Test GitHub CLI authentication - integration test."""
        # Test if GitHub CLI is properly authenticated
        try:
            result = subprocess.run(["gh", "auth", "status"], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.test_repo_dir)
            
            # Should be authenticated successfully
            self.assertEqual(result.returncode, 0)
            self.assertIn("Logged in", result.stdout)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"GitHub CLI authentication test failed: {e}")

    def test_gh_repository_access_integration(self):
        """Test GitHub repository access - integration test."""
        # Test if we can access the test repository
        repo_owner = os.getenv("GITHUB_REPO_OWNER")
        test_repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
        test_repo = f"{repo_owner}/{test_repo_name}" if repo_owner and test_repo_name else None
        if test_repo:
            try:
                result = subprocess.run(["gh", "repo", "view", test_repo], 
                                      capture_output=True, 
                                      text=True,
                                      cwd=self.test_repo_dir)
                
                # Should successfully access repository
                self.assertIn(test_repo, result.stdout)
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.fail(f"GitHub repository access test failed: {e}")

    def test_gh_pr_list_with_real_repository_integration(self):
        """Test listing PRs for real repository - integration test."""
        # Clone test repository to the current directory
        try:
            clone_test_repository(self.test_repo_dir)
        except (ValueError, RuntimeError) as e:
            self.fail(f"Failed to set up git repository for PR list test: {e}")
        
        # Make real call to list PRs
        result = self.github_pr_tools.gh_pr_list()
        
        # Should succeed with real GitHub response
        self.assertIn("Pull Requests", result)


if __name__ == '__main__':
    unittest.main() 