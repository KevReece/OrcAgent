#!/usr/bin/env python3
"""
Test Tool Tracker Module

Integration tests for the tool tracking functionality.
"""

import pytest
from unittest.mock import Mock
from tools.tool_tracker import (
    track_tool_call, 
    set_metrics_tracker, 
    get_tool_name_from_module,
    create_tracked_tools_dict
)


class TestToolTracker:
    """Test cases for tool tracking functionality."""
    
    def test_track_tool_call_success(self):
        """Test tracking successful tool calls."""
        mock_tracker = Mock()
        set_metrics_tracker(mock_tracker)
        
        @track_tool_call("test_tools", "test_function")
        def test_func():
            return "Success"
        
        result = test_func()
        
        assert result == "Success"
        mock_tracker.record_tool_call.assert_called_once_with("test_tools", "test_function", True)
    
    def test_track_tool_call_error_string(self):
        """Test tracking tool calls that return error strings."""
        mock_tracker = Mock()
        set_metrics_tracker(mock_tracker)
        
        @track_tool_call("test_tools", "test_function")
        def test_func():
            return "Error: Something went wrong"
        
        result = test_func()
        
        assert result == "Error: Something went wrong"
        mock_tracker.record_tool_call.assert_called_once_with("test_tools", "test_function", False)
    
    def test_track_tool_call_exception(self):
        """Test tracking tool calls that raise exceptions."""
        mock_tracker = Mock()
        set_metrics_tracker(mock_tracker)
        
        @track_tool_call("test_tools", "test_function")
        def test_func():
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError):
            test_func()
        
        mock_tracker.record_tool_call.assert_called_once_with("test_tools", "test_function", False)
    
    def test_track_tool_call_no_tracker(self):
        """Test tracking when no metrics tracker is set."""
        set_metrics_tracker(None)
        
        @track_tool_call("test_tools", "test_function")
        def test_func():
            return "Success"
        
        result = test_func()
        
        assert result == "Success"
        # Should not raise any exceptions when no tracker is set
    
    def test_get_tool_name_from_module(self):
        """Test extracting tool name from module path."""
        assert get_tool_name_from_module("tools.file_tools") == "file_tools"
        assert get_tool_name_from_module("tools.git_tools") == "git_tools"
        assert get_tool_name_from_module("file_tools") == "file_tools"
        assert get_tool_name_from_module("tools.docker_tools") == "docker_tools"
    
    def test_create_tracked_tools_dict(self):
        """Test creating tracked tools dictionary."""
        def test_func1():
            return "Success 1"
        
        def test_func2():
            return "Success 2"
        
        def _private_func():
            return "Private"
        
        original_tools = {
            "func1": test_func1,
            "func2": test_func2,
            "_private": _private_func,
            "constant": "not_callable"
        }
        
        tracked_tools = create_tracked_tools_dict(original_tools, "test_tools")
        
        # Check that callable functions are wrapped
        assert "func1" in tracked_tools
        assert "func2" in tracked_tools
        assert callable(tracked_tools["func1"])
        assert callable(tracked_tools["func2"])
        
        # Check that non-callable items are preserved
        assert "constant" in tracked_tools
        assert tracked_tools["constant"] == "not_callable"
        
        # Check that private functions are preserved as-is
        assert "_private" in tracked_tools
        assert tracked_tools["_private"] == _private_func
        
        # Test that wrapped functions still work
        result1 = tracked_tools["func1"]()
        result2 = tracked_tools["func2"]()
        
        assert result1 == "Success 1"
        assert result2 == "Success 2"
    
    def test_create_tracked_tools_dict_with_tracker(self):
        """Test creating tracked tools dictionary with metrics tracker."""
        mock_tracker = Mock()
        set_metrics_tracker(mock_tracker)
        
        def test_func():
            return "Success"
        
        original_tools = {
            "test_func": test_func
        }
        
        tracked_tools = create_tracked_tools_dict(original_tools, "test_tools")
        
        # Call the tracked function
        result = tracked_tools["test_func"]()
        
        assert result == "Success"
        mock_tracker.record_tool_call.assert_called_once_with("test_tools", "test_func", True)
    
    def test_agent_context_tracking(self):
        """Test agent context tracking functionality."""
        from tools.tool_tracker import set_current_agent, get_current_agent
        
        # Initially no agent set
        assert get_current_agent() is None
        
        # Set an agent
        set_current_agent("test_agent")
        assert get_current_agent() == "test_agent"
        
        # Set different agent
        set_current_agent("another_agent")
        assert get_current_agent() == "another_agent"
    
    def test_track_tool_call_with_agent_context(self):
        """Test tool call tracking with agent context."""
        mock_tracker = Mock()
        set_metrics_tracker(mock_tracker)
        
        from tools.tool_tracker import set_current_agent
        
        @track_tool_call("test_tools", "test_func")
        def test_func():
            return "Success"
        
        # Set agent context
        set_current_agent("test_agent")
        
        # Call function
        result = test_func()
        
        assert result == "Success"
        mock_tracker.record_tool_call.assert_called_once_with("test_tools", "test_func", True)
        mock_tracker.record_agent_tool_call.assert_called_once_with("test_agent")
    
    def test_set_metrics_tracker(self):
        """Test setting metrics tracker."""
        mock_tracker = Mock()
        
        set_metrics_tracker(mock_tracker)
        
        @track_tool_call("test_tools", "test_function")
        def test_func():
            return "Success"
        
        test_func()
        
        mock_tracker.record_tool_call.assert_called_once_with("test_tools", "test_function", True) 