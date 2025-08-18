#!/usr/bin/env python3
"""
Agent Working Directories Environment Module

This module provides functionality to set up agent working directories with git repository access.
"""

import os
import subprocess
from typing import List, Optional, Tuple
from logger.log_wrapper import get_logger


class WorkingDirectoryAgentEnvironment:
    """Agent working directories management class with git repository setup."""
    
    def __init__(self, is_integration_test: bool = False):
        """
        Initialize agent working directories manager.
        
        Args:
            is_integration_test: Whether to use test repository configuration
        """
        self.repo_owner, self.repo_name, self.github_token = self._get_repo_config(is_integration_test)
        self.logger = get_logger("env:work_dir", __name__)
        
    def _get_repo_config(self, is_integration_test: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get repository configuration from environment variables.
        
        Args:
            is_integration_test: Whether to use test repository configuration
        
        Returns:
            tuple: (repo_owner, repo_name, github_token)
        """
        repo_owner = os.getenv("GITHUB_REPO_OWNER")
        github_token = os.getenv("GITHUB_TOKEN")
        
        if is_integration_test:
            repo_name = os.getenv("GITHUB_TEST_REPO_NAME")
        else:
            repo_name = os.getenv("GITHUB_REPO_NAME")
            
        return repo_owner, repo_name, github_token
    
    def setup_working_directories(self, working_directories: List[str]) -> bool:
        """
        Initialize agent working directories with git repository access.
        This prevents agents from getting stuck in infinite loops when trying to access git.
        
        Args:
            working_directories: List of working directories to set up
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.repo_owner or not self.repo_name:
                self.logger.warning("GitHub repository not configured - agents will work without git repository access")
                return True  # Not a critical failure
            
            # Clone repository into all agent working directories
            for work_dir in working_directories:
                try:
                    # Use gh command to clone repository into working directory
                    repo_url = f"https://github.com/{self.repo_owner}/{self.repo_name}"
                    
                    # Clone the repository contents into the working directory
                    result = subprocess.run([
                        "git", "clone", repo_url, "."
                    ], cwd=work_dir, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        self.logger.info(f"Cloned {repo_url} into {work_dir}")
                    else:
                        self.logger.warning(f"Failed to clone repository into {work_dir}: {result.stderr}")
                        # Continue anyway - not a critical failure
                        
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Repository clone timed out for {work_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clone repository into {work_dir}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup agent working directories: {e}")
            return False
    
    def reset(self) -> None:
        """
        Reset agent working directories by cleaning them.
        This is a no-op for this environment as working directories are temporary.
        """
        self.logger.info("Agent working directories reset (no-op - directories are temporary)") 