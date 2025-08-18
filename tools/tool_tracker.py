#!/usr/bin/env python3
"""
Tool Tracking Module

Provides decorators and utilities to track tool calls for metrics collection.
"""

import functools
from contextvars import ContextVar
from typing import Callable, Any, Optional, Dict
from logger.log_wrapper import get_logger

logger = get_logger("tools:tracker", __name__)

# Global metrics tracker instance
_metrics_tracker: Optional[Any] = None

# Context variable to track the current executing agent
current_agent_context: ContextVar[Optional[str]] = ContextVar('current_agent', default=None)

def set_metrics_tracker(tracker: Any) -> None:
    """Set the global metrics tracker instance."""
    global _metrics_tracker
    _metrics_tracker = tracker
    logger.debug("Metrics tracker set for tool tracking")

def set_current_agent(agent_name: str) -> None:
    """Set the current executing agent in context."""
    current_agent_context.set(agent_name)
    logger.debug(f"Set current agent context to: {agent_name}")

def get_current_agent() -> Optional[str]:
    """Get the current executing agent from context."""
    return current_agent_context.get()

def track_tool_call(tool_name: str, function_name: str):
    """
    Decorator to track tool calls for metrics collection.
    
    Args:
        tool_name: Name of the tool module
        function_name: Name of the function being called
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            success = True
            try:
                result = func(*args, **kwargs)
                # Check if result indicates an error
                if isinstance(result, str) and result.startswith("Error:"):
                    success = False
                return result
            except Exception as e:
                success = False
                logger.error(f"Tool call failed: {tool_name}.{function_name} - {e}")
                raise
            finally:
                # Record the tool call if metrics tracker is available
                if _metrics_tracker is not None:
                    try:
                        _metrics_tracker.record_tool_call(tool_name, function_name, success)
                        # Also update the current agent's tool call count if available
                        current_agent = get_current_agent()
                        if current_agent:
                            _metrics_tracker.record_agent_tool_call(current_agent)
                    except Exception as e:
                        logger.error(f"Failed to record tool call metrics: {e}")
        
        return wrapper
    return decorator

def get_tool_name_from_module(module_path: str) -> str:
    """
    Extract tool name from module path.
    
    Args:
        module_path: Full module path (e.g., 'tools.file_tools')
        
    Returns:
        str: Tool name (e.g., 'file_tools')
    """
    if '.' in module_path:
        return module_path.split('.')[-1]
    return module_path

def create_tracked_tools_dict(tools_dict: Dict[str, Callable], tool_name: str) -> Dict[str, Callable]:
    """
    Create a new tools dictionary with tracking decorators applied.
    
    Args:
        tools_dict: Original tools dictionary
        tool_name: Name of the tool module
        
    Returns:
        Dict[str, Callable]: Tools dictionary with tracking applied
    """
    tracked_tools = {}
    
    for func_name, func in tools_dict.items():
        if callable(func) and not func_name.startswith('_'):
            # Apply tracking decorator
            tracked_func = track_tool_call(tool_name, func_name)(func)
            tracked_tools[func_name] = tracked_func
        else:
            # Keep non-callable items as-is
            tracked_tools[func_name] = func
    
    return tracked_tools 