"""
Integration Tests for Git Tools

Integration tests that require real git installation and fail if prerequisites are missing.
All tests run in isolated system temp directories outside the repository.
"""

import unittest
import os
import shutil
import tempfile
import subprocess
from tools.git_tools import get_tools
from tools.context import ToolsContext


def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True
    )


class TestGitToolsIntegration(unittest.TestCase):
    """Integration tests for Git tools that require real git installation."""
    
    def setUp(self):
        """Set up a temporary directory and initialize a git repository for testing."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_git_test_")
        self.test_repo_dir = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(self.test_repo_dir)
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        # Create git tools instance
        tools = get_tools(make_tools_context(self.test_repo_dir))
        
        class Self:
            def __init__(self, tools):
                self.git_status = tools[0]
                self.git_add = tools[1]
                self.git_commit = tools[2]
                self.git_push = tools[3]
                self.git_pull = tools[4]
                self.git_fetch = tools[5]
                self.git_branch_list = tools[6]
                self.git_branch_create = tools[7]
                self.git_checkout = tools[8]
                self.git_merge = tools[9]
                self.git_stash = tools[10]
                self.git_log = tools[11]
                self.git_diff = tools[12]
                self.git_reset = tools[13]
                self.git_remote_list = tools[14]
                self.git_remote_add = tools[15]
                self.git_tag_list = tools[16]
                self.git_tag_create = tools[17]
                self.git_clean = tools[18]
                self.git_show = tools[19]
                self.git_stash_pop = tools[20]
                self.git_branch = tools[21]
                self.git_remote = tools[22]
        
        self.git_tools = Self(tools)
        
        # Ensure git is available - fail if not found
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"Git not found. This is a required prerequisite for integration tests: {e}")
        
        # Initialize a git repository - fail if this fails
        try:
            subprocess.run(["git", "init", "--initial-branch=main"], cwd=self.test_repo_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.test_repo_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_repo_dir, check=True)
            
            # Create an initial commit
            test_file = os.path.join(self.test_repo_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Initial content")
            subprocess.run(["git", "add", "test.txt"], cwd=self.test_repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.test_repo_dir, check=True)
            
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"Failed to initialize git repository. Git must be properly configured: {e}")
    
    def tearDown(self):
        """Clean up the temporary directory."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_git_status_integration(self):
        """Test git status functionality with real git."""
        result = self.git_tools.git_status()
        self.assertIn("working tree clean", result.lower())
    
    def test_git_add_integration(self):
        """Test git add functionality with real git."""
        # Create a new file
        new_file = os.path.join(self.test_repo_dir, "new_file.txt")
        with open(new_file, 'w') as f:
            f.write("New content")
        
        result = self.git_tools.git_add("new_file.txt")
        self.assertIn("successful", result.lower())
        
        # Verify file was staged
        status_result = self.git_tools.git_status()
        self.assertTrue("new_file.txt" in status_result and "new file:" in status_result.lower())
    
    def test_git_add_all_integration(self):
        """Test git add all functionality with real git."""
        # Create multiple new files
        for i in range(3):
            new_file = os.path.join(self.test_repo_dir, f"file_{i}.txt")
            with open(new_file, 'w') as f:
                f.write(f"Content {i}")
        
        result = self.git_tools.git_add(".")
        self.assertIn("successful", result.lower())
    
    def test_git_commit_integration(self):
        """Test git commit functionality with real git."""
        # Create and add a new file
        new_file = os.path.join(self.test_repo_dir, "commit_test.txt")
        with open(new_file, 'w') as f:
            f.write("Commit test content")
        
        self.git_tools.git_add("commit_test.txt")
        
        result = self.git_tools.git_commit("Test commit message")
        self.assertIn("successful", result.lower())
    
    def test_git_push_integration(self):
        """Test git push functionality - should fail appropriately when no remote."""
        result = self.git_tools.git_push()
        # Should get an error about no remote configured
        self.assertTrue("no remote" in result.lower() or "fatal" in result.lower() or "error" in result.lower())
    
    def test_git_pull_integration(self):
        """Test git pull functionality - should fail appropriately when no remote."""
        result = self.git_tools.git_pull()
        # Should get an error about no remote configured
        self.assertTrue("no remote" in result.lower() or "fatal" in result.lower() or "error" in result.lower())
    
    def test_git_fetch_integration(self):
        """Test git fetch functionality - should fail appropriately when no remote."""
        result = self.git_tools.git_fetch()
        # Should get an error about no remote configured
        self.assertTrue("no remote" in result.lower() or "fatal" in result.lower() or "error" in result.lower())
    
    def test_git_branch_list_integration(self):
        """Test git branch listing with real git."""
        result = self.git_tools.git_branch()
        self.assertIn("main", result.lower())
    
    def test_git_branch_create_integration(self):
        """Test git branch creation with real git."""
        result = self.git_tools.git_branch("test-branch")
        self.assertIn("successful", result.lower())
        
        # Verify branch was created
        branch_list = self.git_tools.git_branch()
        self.assertIn("test-branch", branch_list)
    
    def test_git_checkout_integration(self):
        """Test git checkout functionality with real git."""
        # Create a new branch first
        self.git_tools.git_branch("checkout-test")
        
        result = self.git_tools.git_checkout("checkout-test")
        self.assertIn("successful", result.lower())
        
        # Verify we're on the new branch
        branch_result = self.git_tools.git_branch()
        self.assertIn("* checkout-test", branch_result)
    
    def test_git_merge_integration(self):
        """Test git merge functionality with real git."""
        # Create and commit on a new branch
        self.git_tools.git_branch("merge-test")
        self.git_tools.git_checkout("merge-test")
        
        # Create a file on the branch
        merge_file = os.path.join(self.test_repo_dir, "merge_file.txt")
        with open(merge_file, 'w') as f:
            f.write("Merge test content")
        
        self.git_tools.git_add("merge_file.txt")
        self.git_tools.git_commit("Add merge test file")
        
        # Switch back to main and merge
        self.git_tools.git_checkout("main")
        result = self.git_tools.git_merge("merge-test")
        
        # Should be successful or already up to date
        self.assertTrue("successful" in result.lower() or "up to date" in result.lower())
    
    def test_git_log_integration(self):
        """Test git log functionality with real git."""
        result = self.git_tools.git_log()
        self.assertIn("Initial commit", result)
    
    def test_git_diff_integration(self):
        """Test git diff functionality with real git."""
        # Modify a file
        test_file = os.path.join(self.test_repo_dir, "test.txt")
        with open(test_file, 'a') as f:
            f.write("\nModified content")
        
        result = self.git_tools.git_diff()
        self.assertIn("Modified content", result)
    
    def test_git_stash_integration(self):
        """Test git stash functionality with real git."""
        # Modify a file first
        test_file = os.path.join(self.test_repo_dir, "test.txt")
        with open(test_file, 'a') as f:
            f.write("\nStash test content")
        
        result = self.git_tools.git_stash()
        self.assertIn("successful", result.lower())
    
    def test_git_stash_pop_integration(self):
        """Test git stash pop functionality with real git."""
        # Stash something first
        test_file = os.path.join(self.test_repo_dir, "test.txt")
        with open(test_file, 'a') as f:
            f.write("\nStash pop test content")
        
        self.git_tools.git_stash()
        
        result = self.git_tools.git_stash_pop()
        # Should either pop successfully or indicate no stash
        self.assertTrue("successful" in result.lower() or "no stash" in result.lower())
    
    def test_git_reset_integration(self):
        """Test git reset functionality with real git."""
        # Create and stage a file
        reset_file = os.path.join(self.test_repo_dir, "reset_test.txt")
        with open(reset_file, 'w') as f:
            f.write("Reset test content")
        
        self.git_tools.git_add("reset_test.txt")
        
        result = self.git_tools.git_reset()
        self.assertIn("successful", result.lower())
    
    def test_git_clean_integration(self):
        """Test git clean functionality with real git."""
        # Create untracked files
        for i in range(2):
            untracked_file = os.path.join(self.test_repo_dir, f"untracked_{i}.txt")
            with open(untracked_file, 'w') as f:
                f.write(f"Untracked content {i}")
        
        result = self.git_tools.git_clean()
        self.assertIn("successful", result.lower())
    
    def test_git_remote_add_integration(self):
        """Test git remote add functionality with real git."""
        result = self.git_tools.git_remote_add("origin", "https://github.com/test/repo.git")
        self.assertIn("successful", result.lower())
        
        # Verify remote was added
        remote_result = self.git_tools.git_remote()
        self.assertIn("origin", remote_result)
    
    def test_git_remote_list_integration(self):
        """Test git remote listing with real git."""
        result = self.git_tools.git_remote()
        # Should return something, even if empty
        self.assertIsInstance(result, str)
    
    def test_git_show_integration(self):
        """Test git show functionality with real git."""
        result = self.git_tools.git_show("HEAD")
        self.assertIn("Initial commit", result)


class TestGitToolsErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling in git tools."""
    
    def setUp(self):
        """Set up a temporary directory without git repository."""
        # Create temp directory in system temp location, outside repository
        self.temp_dir = tempfile.mkdtemp(prefix="orcagent_git_error_test_")
        tools = get_tools(make_tools_context(self.temp_dir))
        
        class Self:
            def __init__(self, tools):
                self.git_status = tools[0]
                self.git_add = tools[1]
                self.git_commit = tools[2]
                self.git_push = tools[3]
                self.git_pull = tools[4]
                self.git_fetch = tools[5]
                self.git_branch_list = tools[6]
                self.git_branch_create = tools[7]
                self.git_checkout = tools[8]
                self.git_merge = tools[9]
                self.git_stash = tools[10]
                self.git_log = tools[11]
                self.git_diff = tools[12]
                self.git_reset = tools[13]
                self.git_remote_list = tools[14]
                self.git_remote_add = tools[15]
                self.git_tag_list = tools[16]
                self.git_tag_create = tools[17]
                self.git_clean = tools[18]
                self.git_show = tools[19]
                self.git_stash_pop = tools[20]
                self.git_branch = tools[21]
                self.git_remote = tools[22]
        
        self.git_tools = Self(tools)
        
        # Verify we're outside the repository
        current_repo_path = os.path.abspath(os.path.dirname(__file__))
        temp_path = os.path.abspath(self.temp_dir)
        if temp_path.startswith(current_repo_path):
            self.fail(f"Test temp directory {temp_path} is inside repository {current_repo_path}. This violates isolation requirements.")
        
        # Ensure git is available - fail if not found
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.fail(f"Git not found. This is a required prerequisite for integration tests: {e}")
    
    def tearDown(self):
        """Clean up the temporary directory."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_git_status_non_git_directory_integration(self):
        """Test git status in non-git directory with real git."""
        result = self.git_tools.git_status()
        self.assertIn("not a git repository", result.lower())
    
    def test_git_add_non_existent_file_integration(self):
        """Test git add with non-existent file with real git."""
        # Initialize git repo first
        subprocess.run(["git", "init", "--initial-branch=main"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)
        
        result = self.git_tools.git_add("non_existent_file.txt")
        self.assertIn("did not match any files", result.lower())
    
    def test_git_commit_no_changes_integration(self):
        """Test git commit with no changes with real git."""
        # Initialize git repo first
        subprocess.run(["git", "init", "--initial-branch=main"], cwd=self.temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, check=True)
        
        result = self.git_tools.git_commit("Empty commit")
        self.assertIn("nothing to commit", result.lower())


if __name__ == '__main__':
    unittest.main() 