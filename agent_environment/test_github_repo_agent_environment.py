"""
Basic tests for GitHubRepoAgentEnvironment class.
"""

import unittest
import os
import tempfile
import subprocess
import json
import uuid
from agent_environment.github_repo_agent_environment import GitHubRepoAgentEnvironment
from dotenv import load_dotenv

load_dotenv(override=True)


class TestGitHubRepoIntegration(unittest.TestCase):
    """Integration tests using real GitHub repository."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER")
        self.test_repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
        
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        if not self.repo_owner:
            self.fail("GITHUB_REPO_OWNER environment variable is required for integration tests")
        
        if not self.test_repo_name:
            self.fail("GITHUB_TEST_REPO_NAME environment variable is required for integration tests")
        
        if not self.github_token:
            self.fail("GITHUB_TOKEN environment variable is required for integration tests")
        
        self.repo = GitHubRepoAgentEnvironment(is_integration_test=True)
        
    def test_full_clean_operation(self):
        """
        Full integration test of repository cleaning and seeding.
        
        This test:
        1. Clones the test repository and adds content
        2. Runs the clean+seed operation  
        3. Verifies the repository contains the seeded files after cleaning
        
        WARNING: This test will CLEAN the test repository specified in GITHUB_REPO_OWNER/GITHUB_TEST_REPO_NAME
        Make sure it's a dedicated test repository that can be safely wiped.
        """
        # Create a temporary directory to avoid running in main codebase
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            
            try:
                os.chdir(temp_dir)
                
                # Step 1: Clone the test repository and add content
                clone_url = f"https://{self.github_token}@github.com/{self.repo.repo_full_name}.git"
                
                clone_result = subprocess.run([
                    "git", "clone", clone_url, "test_repo"
                ], capture_output=True, text=True)
                
                if clone_result.returncode != 0:
                    self.fail(f"Failed to clone test repository: {clone_result.stderr}")
                
                os.chdir("test_repo")
                
                # Configure git user for commits
                subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
                subprocess.run(["git", "config", "user.name", "Test User"], check=True)
                
                # Create test files to ensure repository has content before cleaning
                with open("test_file.txt", "w") as f:
                    f.write("This is a test file that should be cleaned up")
                
                with open("README.md", "w") as f:
                    f.write("# Test Repository\n\nThis repository is used for testing cleanup operations.")
                
                with open("sample.py", "w") as f:
                    f.write("# Sample Python file\nprint('This will be cleaned up')")
                
                # Add, commit and push the test files
                subprocess.run(["git", "add", "."], check=True)
                
                # Check if there are any changes to commit
                status_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                if status_result.stdout.strip():
                    subprocess.run(["git", "commit", "-m", "Add test files for cleanup test"], check=True)
                else:
                    # If no changes, create a dummy commit to ensure we have something to clean
                    subprocess.run(["git", "commit", "--allow-empty", "-m", "Empty commit for cleanup test"], check=True)
                
                # Try to push, handling different branch scenarios
                push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
                if push_result.returncode != 0:
                    # Try setting upstream for main branch
                    push_result = subprocess.run(["git", "push", "--set-upstream", "origin", "main"], capture_output=True, text=True)
                    if push_result.returncode != 0:
                        # Try setting upstream for master branch
                        push_result = subprocess.run(["git", "push", "--set-upstream", "origin", "master"], capture_output=True, text=True)
                        if push_result.returncode != 0:
                            self.fail(f"Failed to push test files: {push_result.stderr}")

                # Determine default branch using gh
                default_branch_res = subprocess.run([
                    "gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"
                ], capture_output=True, text=True)
                if default_branch_res.returncode != 0 or not default_branch_res.stdout.strip():
                    self.fail(f"Failed to resolve default branch: {default_branch_res.stderr}")
                default_branch = default_branch_res.stdout.strip()

                # Create a non-default branch and push it
                branch_name = f"cleanup-test-{uuid.uuid4().hex[:8]}"
                checkout_res = subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True, text=True)
                if checkout_res.returncode != 0:
                    self.fail(f"Failed to create branch: {checkout_res.stderr}")
                with open("branch_file.txt", "w") as f:
                    f.write("branch data\n")
                subprocess.run(["git", "add", "branch_file.txt"], check=True)
                subprocess.run(["git", "commit", "-m", f"Add branch file for {branch_name}"], check=True)
                push_branch = subprocess.run(["git", "push", "--set-upstream", "origin", branch_name], capture_output=True, text=True)
                if push_branch.returncode != 0:
                    self.fail(f"Failed to push branch {branch_name}: {push_branch.stderr}")

                # Create a draft PR from the new branch to default branch
                pr_create = subprocess.run([
                    "gh", "pr", "create",
                    "--base", default_branch,
                    "--head", branch_name,
                    "--title", f"Test PR for {branch_name}",
                    "--body", "Automated test PR",
                    "--draft"
                ], capture_output=True, text=True)
                if pr_create.returncode != 0:
                    self.fail(f"Failed to create PR for {branch_name}: {pr_create.stderr}")

                # Verify PR exists and is open for this head branch
                pr_list_before = subprocess.run([
                    "gh", "pr", "list", "--state", "open", "--json", "number,headRefName"
                ], capture_output=True, text=True)
                self.assertEqual(pr_list_before.returncode, 0, f"Failed to list PRs: {pr_list_before.stderr}")
                open_prs = json.loads(pr_list_before.stdout) if pr_list_before.stdout else []
                self.assertTrue(any(p.get("headRefName") == branch_name for p in open_prs), "Expected open PR for test branch before reset")
                
                # Go back to temp directory root
                os.chdir(temp_dir)
                
                # Step 2: Run the clean operation and assert the result
                try:
                    self.repo.reset()
                except Exception as e:
                    self.fail(f"Clean operation failed: {e}")
                
                # Step 3: Verify the repository contains the seeded files after cleaning
                # Clone again to check the current state
                clone_result = subprocess.run([
                    "git", "clone", clone_url, "test_repo_after"
                ], capture_output=True, text=True)
                
                if clone_result.returncode != 0:
                    self.fail(f"Failed to clone repository for verification: {clone_result.stderr}")
                
                # Verify using git ls-files (which shows tracked files)
                os.chdir("test_repo_after")
                git_files_result = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
                tracked_files = [f for f in git_files_result.stdout.strip().split('\n') if f.strip()]

                expected_seeded = {
                    "Dockerfile",
                    "nginx.conf",
                    "index.html",
                    ".github/workflows/deploy.yml",
                }

                missing = [p for p in expected_seeded if p not in tracked_files]
                self.assertEqual(len(missing), 0, f"Missing seeded files after reset: {missing}. Tracked: {tracked_files}")

                # Verify the non-default branch was deleted from remote
                ls_remote = subprocess.run(["git", "ls-remote", "--heads", "origin", branch_name], capture_output=True, text=True)
                self.assertEqual(ls_remote.returncode, 0, f"git ls-remote failed: {ls_remote.stderr}")
                self.assertEqual(ls_remote.stdout.strip(), "", f"Branch {branch_name} still exists on remote after reset")

                # Verify the PR for that branch is now closed
                pr_list_after = subprocess.run([
                    "gh", "pr", "list", "--state", "closed", "--json", "number,headRefName"
                ], capture_output=True, text=True)
                self.assertEqual(pr_list_after.returncode, 0, f"Failed to list PRs after reset: {pr_list_after.stderr}")
                closed_prs = json.loads(pr_list_after.stdout) if pr_list_after.stdout else []
                self.assertTrue(any(p.get("headRefName") == branch_name for p in closed_prs), "Expected PR for test branch to be closed after reset")
                
            except subprocess.CalledProcessError as e:
                self.fail(f"Git operation failed: {e}")
            finally:
                os.chdir(original_cwd)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 