#!/usr/bin/env python3
"""
Rate Limiting Handler for OpenAI API

Provides exponential backoff with jitter for handling OpenAI rate limit errors.
"""

import time
import random
from typing import Callable, Any, Optional
from openai import RateLimitError
from logger.log_wrapper import get_logger
from configuration import (
    RATE_LIMIT_MAX_RETRIES,
    RATE_LIMIT_BASE_DELAY,
    RATE_LIMIT_MAX_DELAY,
    RATE_LIMIT_JITTER
)

logger = get_logger("rate_limit_handler", __name__)


def calculate_backoff_delay(attempt: int, base_delay: float = RATE_LIMIT_BASE_DELAY, 
                          max_delay: float = RATE_LIMIT_MAX_DELAY, 
                          jitter_factor: float = RATE_LIMIT_JITTER) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter_factor: Jitter factor (0.0 to 1.0)
        
    Returns:
        float: Delay in seconds
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # Add jitter to prevent thundering herd
    jitter = delay * jitter_factor * random.uniform(-1, 1)
    final_delay = max(0, delay + jitter)
    
    return final_delay


def handle_rate_limit_with_retry(func: Callable, *args, timeout: Optional[float] = None, **kwargs) -> Any:
    """
    Execute a function with rate limit retry logic and optional timeout.
    
    Args:
        func: Function to execute
        *args: Function arguments
        timeout: Optional timeout in seconds for the entire operation
        **kwargs: Function keyword arguments
        
    Returns:
        Any: Function result
        
    Raises:
        RateLimitError: If max retries exceeded
        TimeoutError: If operation times out
        Exception: Any other exception from the function
    """
    import signal
    from functools import wraps
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    # Create a timeout wrapper if timeout is specified
    if timeout is not None:
        def timeout_wrapper(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Set up signal handler for timeout
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout))
                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)  # Cancel the alarm
                    return result
                finally:
                    signal.signal(signal.SIGALRM, old_handler)  # Restore original handler
            return wrapper
        func = timeout_wrapper(func)
    
    last_exception: Optional[Exception] = None
    rate_limit_count = 0
    
    for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
            
        except RateLimitError as e:
            last_exception = e
            rate_limit_count += 1
            
            if attempt == RATE_LIMIT_MAX_RETRIES:
                logger.error(f"Rate limit exceeded after {RATE_LIMIT_MAX_RETRIES} retries. "
                           f"Total rate limit hits: {rate_limit_count}")
                raise e
            
            delay = calculate_backoff_delay(attempt)
            logger.warning(f"Rate limit hit (attempt {attempt + 1}/{RATE_LIMIT_MAX_RETRIES + 1}, "
                         f"total hits: {rate_limit_count}). Retrying in {delay:.2f}s...")
            
            time.sleep(delay)
            
        except Exception as e:
            # Re-raise non-rate-limit exceptions immediately
            raise e
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception


def create_rate_limited_config(config_list: list) -> list:
    """
    Create a rate-limited configuration for AutoGen.
    
    Args:
        config_list: Original config list
        
    Returns:
        list: Config list (unchanged - rate limiting handled at agent level)
    """
    # Return config list unchanged - rate limiting is handled at the agent level
    # through the RateLimitedAssistantAgent and RateLimitedUserProxyAgent classes
    return config_list 