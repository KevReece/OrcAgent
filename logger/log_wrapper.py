#!/usr/bin/env python3
"""
Logging Wrapper Module

Provides consistent logging with prefixes for different components.
"""

import logging
from typing import Optional


class PrefixedLogger:
    """Logger wrapper that adds consistent prefixes to all log messages."""
    
    def __init__(self, prefix: str, logger_name: Optional[str] = None):
        self.logger = logging.getLogger(logger_name or __name__)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(f"⚠️ {message}")
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(f"❌ {message}")
    

def get_logger(component: str, logger_name: Optional[str] = None) -> PrefixedLogger:
    """
    Get a prefixed logger for a specific component.
    
    Args:
        component: Short name for the component (e.g., 'main', 'env:notion', 'tool:fs')
        logger_name: Optional logger name, defaults to calling module
    
    Returns:
        PrefixedLogger instance
    """
    return PrefixedLogger(component, logger_name) 