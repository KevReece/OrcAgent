#!/usr/bin/env python3
"""
Repository Dumper Module

This module provides functionality to dump complete repository data to log files.
"""

import os
import json
from typing import Dict, Any
from logger.log_wrapper import get_logger

logger = get_logger("logger:repository_dumper", __name__)


def dump_repository_on_exit(log_filename: str) -> None:
    """
    Dump complete RoleRepository data including all roles, workers, and memories to a log file on main exit.
    
    Args:
        log_filename: Path to the main log file to determine log directory
    """
    try:
        from agents.role_repository import RoleRepository
        
        log_dir = os.path.dirname(log_filename)
        
        # Get the RoleRepository singleton instance
        repository = RoleRepository()
        
        # Get complete repository JSON data
        repository_data = repository.dump_repository_to_json()
        
        # Write JSON data to file
        dump_file = os.path.join(log_dir, "role_repository.log")
        with open(dump_file, 'w') as f:
            json.dump(repository_data, f, indent=2)
        
        logger.info(f"RoleRepository data dumped to: {dump_file}")
        
    except Exception as e:
        logger.error(f"Failed to dump repository data on exit: {e}")
        import traceback
        logger.error(f"Repository dump traceback: {traceback.format_exc()}") 