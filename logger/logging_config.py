#!/usr/bin/env python3
"""
Logging Configuration Module

This module provides structured logging configuration for the agent system.
"""

import logging
import os
import sys


def setup_logging(run_dir: str) -> str:
    """
    Set up structured logging for the agent run.
    
    Args:
        run_dir: Directory for the current run
        
    Returns:
        str: Path to the log file
    """
    # Configure basic logging for console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    log_dir = os.path.join(run_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = os.path.join(log_dir, "orcagent_run.log")
    
    # Create file handler for detailed logging
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Add file handler to root logger
    logging.getLogger().addHandler(file_handler)
    
    return log_filename 