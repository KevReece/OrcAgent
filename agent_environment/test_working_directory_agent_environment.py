"""
Basic tests for WorkingDirectoryAgentEnvironment class.
"""

import unittest
import os
import tempfile
import shutil
from agent_environment.working_directory_agent_environment import WorkingDirectoryAgentEnvironment
from dotenv import load_dotenv
from logger.log_wrapper import get_logger

load_dotenv(override=True)


class TestWorkingDirectoryAgentEnvironmentIntegration(unittest.TestCase):
    """Integration tests using real GitHub repository and file system operations."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.logger = get_logger("test:work_dir", __name__)
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER")
        self.repo_name = os.getenv("GITHUB_TEST_REPO_NAME")  # Use test repo for integration tests
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        if not self.repo_owner:
            self.fail("GITHUB_REPO_OWNER environment variable is required for integration tests")
        
        if not self.repo_name:
            self.fail("GITHUB_TEST_REPO_NAME environment variable is required for integration tests")
        
        if not self.github_token:
            self.fail("GITHUB_TOKEN environment variable is required for integration tests")
        
        self.working_dir_env = WorkingDirectoryAgentEnvironment(is_integration_test=True)
        
        # Create temporary working directories for testing
        self.temp_dirs = []
        for i in range(3):  # Create 3 test working directories
            temp_dir = tempfile.mkdtemp(prefix=f'test_agent_workdir_{i}_')
            self.temp_dirs.append(temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directories
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def test_setup_working_directories_success(self):
        """
        Test successful setup of working directories with git repository cloning.
        
        This test verifies that:
        1. Repository is cloned directly into each working directory
        2. Git repository is properly initialized in each directory (.git folder exists)
        """
        # Test the setup operation
        result = self.working_dir_env.setup_working_directories(self.temp_dirs)
        
        # Assert setup was successful
        self.assertTrue(result, "setup_working_directories should return True on success")
        
        # Verify each working directory has the cloned repository (directly in the working directory)
        for work_dir in self.temp_dirs:
            # Verify it's a valid git repository (git files should be directly in work_dir)
            git_dir = os.path.join(work_dir, ".git")
            self.assertTrue(os.path.exists(git_dir), 
                          f"Git repository should be initialized in {work_dir}")
            
            # Verify .git is actually a directory (not a file)
            self.assertTrue(os.path.isdir(git_dir),
                          f".git should be a directory in {work_dir}")
            
            self.logger.info(f"Successfully verified git repository in {work_dir}")
    
    def test_setup_working_directories_empty_list(self):
        """Test setup with empty working directories list."""
        result = self.working_dir_env.setup_working_directories([])
        self.assertTrue(result, "setup_working_directories should handle empty list gracefully")
    
    def test_setup_working_directories_invalid_directory(self):
        """Test setup with invalid/non-existent working directory."""
        invalid_dirs = ["/path/that/does/not/exist/and/cannot/be/created"]
        
        # This should not fail catastrophically, but should handle the error gracefully
        result = self.working_dir_env.setup_working_directories(invalid_dirs)
        
        # The method should still return True as it's designed to be non-critical
        self.assertTrue(result, "setup_working_directories should handle invalid directories gracefully")
    
    def test_reset_operation(self):
        """Test the reset operation."""
        # Reset should always succeed as it's currently a no-op
        try:
            self.working_dir_env.reset()
        except Exception as e:
            self.fail(f"Reset operation should not fail: {e}")


class TestWorkingDirectoryAgentEnvironmentMissingConfig(unittest.TestCase):
    """Tests for WorkingDirectoryAgentEnvironment with missing configuration."""
    
    def setUp(self):
        """Set up test fixtures with missing environment variables."""
        # Store original environment variables
        self.original_repo_owner = os.getenv("GITHUB_REPO_OWNER")
        self.original_repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
        self.original_github_token = os.getenv("GITHUB_TOKEN")
    
    def tearDown(self):
        """Restore original environment variables."""
        if self.original_repo_owner:
            os.environ["GITHUB_REPO_OWNER"] = self.original_repo_owner
        elif "GITHUB_REPO_OWNER" in os.environ:
            del os.environ["GITHUB_REPO_OWNER"]
            
        if self.original_repo_name:
            os.environ["GITHUB_TEST_REPO_NAME"] = self.original_repo_name
        elif "GITHUB_TEST_REPO_NAME" in os.environ:
            del os.environ["GITHUB_TEST_REPO_NAME"]
            
        if self.original_github_token:
            os.environ["GITHUB_TOKEN"] = self.original_github_token
        elif "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]
    
    def test_missing_repo_owner(self):
        """Test behavior when GITHUB_REPO_OWNER is missing."""
        # Remove the environment variable
        if "GITHUB_REPO_OWNER" in os.environ:
            del os.environ["GITHUB_REPO_OWNER"]
        
        working_dir_env = WorkingDirectoryAgentEnvironment(is_integration_test=True)
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dirs = [temp_dir]
            
            # Should return True but log warning about missing configuration
            result = working_dir_env.setup_working_directories(temp_dirs)
            self.assertTrue(result, "Should handle missing repo owner gracefully")
            
            # Verify no repository was cloned (no .git directory in working directory)
            git_dir = os.path.join(temp_dir, ".git")
            self.assertFalse(os.path.exists(git_dir),
                           "No repository should be cloned when config is missing")
    
    def test_missing_repo_name(self):
        """Test behavior when GITHUB_TEST_REPO_NAME is missing."""
        # Remove the environment variable
        if "GITHUB_TEST_REPO_NAME" in os.environ:
            del os.environ["GITHUB_TEST_REPO_NAME"]
        
        working_dir_env = WorkingDirectoryAgentEnvironment(is_integration_test=True)
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dirs = [temp_dir]
            
            # Should return True but log warning about missing configuration
            result = working_dir_env.setup_working_directories(temp_dirs)
            self.assertTrue(result, "Should handle missing repo name gracefully")
            
            # Verify no repository was cloned (no .git directory in working directory)
            git_dir = os.path.join(temp_dir, ".git")
            self.assertFalse(os.path.exists(git_dir),
                           "No repository should be cloned when config is missing")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 