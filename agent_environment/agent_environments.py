#!/usr/bin/env python3
"""
Agent Environments Clean Module

This module provides functionality to clean all agent environments.
"""

import os
from typing import List

# Import agent environments
from agent_environment.github_repo_agent_environment import GitHubRepoAgentEnvironment
from agent_environment.notion_page_agent_environment import NotionPageAgentEnvironment
from agent_environment.aws_fargate_agent_environment import AWSFargateAgentEnvironment
from agent_environment.working_directory_agent_environment import WorkingDirectoryAgentEnvironment
from logger.log_wrapper import get_logger

logger = get_logger("env:setup", __name__)


def setup_agent_working_directories(working_directories: List[str]) -> bool:
    """
    Set up agent working directories with git repository access.
    
    Args:
        working_directories: List of working directories to set up
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Setting up agent working directories")
    try:
        working_dirs_env = WorkingDirectoryAgentEnvironment()
        result = working_dirs_env.setup_working_directories(working_directories)
        if result:
            logger.info("Agent working directories setup successfully")
        else:
            logger.warning("Agent working directories setup had issues")
        return result
    except Exception as e:
        logger.error(f"Failed to setup agent working directories: {e}")
        return False


def reset_environments() -> None:
    """
    Reset all agent environments by creating them just-in-time.
    
    Raises:
        Exception: If any environment initialization or reset fails
    """
    logger.info(f"Starting environment reset - Current working directory: {os.getcwd()}")
    
    try:
        # Clean Notion page
        notion_env = NotionPageAgentEnvironment()
        logger.info(f"Resetting Notion page: {notion_env.page_id}")
        notion_env.reset()
        
        # Clean AWS Fargate environment
        aws_env = AWSFargateAgentEnvironment()
        logger.info(f"Resetting AWS Fargate account environment: {aws_env.account_environment} in region: {aws_env.aws_region}")
        aws_env.reset()

        # Clean GitHub repository
        github_env = GitHubRepoAgentEnvironment()
        logger.info(f"Resetting GitHub repository: {github_env.repo_full_name}")
        github_env.reset()
        
        logger.info("Environment reset completed successfully!")
        
    except Exception as e:
        logger.error(f"Environment reset failed: {e}")
        raise 