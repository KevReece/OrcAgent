#!/usr/bin/env python3
"""
Test Metrics Tracker Module

Integration tests for the metrics tracking functionality.
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from metrics.metrics_tracker import MetricsTracker, ExecutionMetrics, AgentMetrics, ToolCallMetrics


class TestMetricsTracker:
    """Test cases for MetricsTracker class."""
    
    def test_metrics_tracker_initialization(self):
        """Test MetricsTracker initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            assert tracker.run_dir == temp_dir
            assert tracker.metrics.timestamp is not None
            assert tracker.metrics.model == ""
            assert tracker.metrics.agents_mode == ""
            assert tracker.metrics.prompt == ""
            assert tracker.metrics.agents == []
            assert tracker.metrics.tool_groups == {}
            assert tracker.metrics.tool_functions == {}
            assert tracker.metrics.total_tokens == 0
            assert tracker.metrics.total_agent_responses == 0
            assert tracker.metrics.total_tool_calls == 0
            assert tracker.metrics.success is False
    
    def test_start_execution(self):
        """Test starting execution tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.start_execution("gpt-4", "team", "Test prompt")
            
            assert tracker.metrics.model == "gpt-4"
            assert tracker.metrics.agents_mode == "team"
            assert tracker.metrics.prompt == "Test prompt"
            assert tracker.start_time is not None
    
    def test_add_agent(self):
        """Test adding agents to tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.add_agent("agent1", "worker")
            tracker.add_agent("agent2", "executor")
            
            assert len(tracker.agent_metrics) == 2
            assert "agent1" in tracker.agent_metrics
            assert "agent2" in tracker.agent_metrics
            assert tracker.agent_metrics["agent1"].agent_type == "worker"
            assert tracker.agent_metrics["agent2"].agent_type == "executor"
            
            assert len(tracker.metrics.agents) == 2
            assert tracker.metrics.agents[0]["name"] == "agent1"
            assert tracker.metrics.agents[1]["name"] == "agent2"
    
    def test_record_agent_response(self):
        """Test recording agent responses."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.add_agent("agent1", "worker")
            tracker.record_agent_response("agent1", 100)
            tracker.record_agent_response("agent1", 150)
            
            assert tracker.agent_metrics["agent1"].response_count == 2
            assert tracker.agent_metrics["agent1"].total_tokens == 250
            assert tracker.metrics.total_agent_responses == 2
            assert tracker.metrics.total_tokens == 250
    
    def test_record_tool_call(self):
        """Test recording tool calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.record_tool_call("file_tools", "read_file", True)
            tracker.record_tool_call("git_tools", "commit", True)
            tracker.record_tool_call("file_tools", "read_file", False)
            
            assert tracker.metrics.total_tool_calls == 3
            assert len(tracker.tool_metrics) == 2
            
            file_tool_key = "file_tools:read_file"
            git_tool_key = "git_tools:commit"
            
            assert file_tool_key in tracker.tool_metrics
            assert git_tool_key in tracker.tool_metrics
            assert tracker.tool_metrics[file_tool_key].call_count == 2
            assert tracker.tool_metrics[file_tool_key].success_count == 1
            assert tracker.tool_metrics[file_tool_key].error_count == 1
            assert tracker.tool_metrics[git_tool_key].call_count == 1
            assert tracker.tool_metrics[git_tool_key].success_count == 1
            assert tracker.tool_metrics[git_tool_key].error_count == 0
    
    def test_tool_group_categorization(self):
        """Test tool group categorization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            # Test different tool groups - each call increments the count
            tracker.record_tool_call("git_tools", "commit")
            tracker.record_tool_call("docker_tools", "build")
            tracker.record_tool_call("aws_cli_tools", "deploy")
            tracker.record_tool_call("notion_tools", "create_page")
            tracker.record_tool_call("github_pr_tools", "create_pr")
            tracker.record_tool_call("file_tools", "read_file")
            tracker.record_tool_call("memory_tools", "store")
            tracker.record_tool_call("delegation_tools", "delegate")
            tracker.record_tool_call("agents_orchestration_tools", "orchestrate")
            tracker.record_tool_call("unknown_tools", "unknown")
            
            # Each tool call increments the count for its group
            assert tracker.metrics.tool_groups["git"] == 1
            assert tracker.metrics.tool_groups["docker"] == 1
            assert tracker.metrics.tool_groups["aws"] == 1
            assert tracker.metrics.tool_groups["notion"] == 1
            assert tracker.metrics.tool_groups["github"] == 1
            assert tracker.metrics.tool_groups["file"] == 1
            assert tracker.metrics.tool_groups["memory"] == 1
            assert tracker.metrics.tool_groups["delegation"] == 1
            assert tracker.metrics.tool_groups["orchestration"] == 1
            assert tracker.metrics.tool_groups["other"] == 1
            
            # Test multiple calls to same tool group
            tracker.record_tool_call("git_tools", "pull")
            tracker.record_tool_call("file_tools", "write_file")
            
            assert tracker.metrics.tool_groups["git"] == 2
            assert tracker.metrics.tool_groups["file"] == 2
    
    def test_record_agent_tool_call(self):
        """Test recording tool calls for specific agents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            # Add agents
            tracker.add_agent("agent1", "worker")
            tracker.add_agent("agent2", "executor")
            
            # Record tool calls for specific agents
            tracker.record_agent_tool_call("agent1")
            tracker.record_agent_tool_call("agent1")
            tracker.record_agent_tool_call("agent2")
            
            # Check agent metrics were updated
            assert tracker.agent_metrics["agent1"].tool_calls == 2
            assert tracker.agent_metrics["agent2"].tool_calls == 1
            
            # Check agents list was updated
            agent1_data = next(agent for agent in tracker.metrics.agents if agent["name"] == "agent1")
            agent2_data = next(agent for agent in tracker.metrics.agents if agent["name"] == "agent2")
            assert agent1_data["tool_calls"] == 2
            assert agent2_data["tool_calls"] == 1
    
    def test_complete_execution(self):
        """Test completing execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.start_execution("gpt-4", "team", "Test prompt")
            tracker.add_agent("agent1", "worker")
            tracker.record_agent_response("agent1", 100)
            tracker.record_tool_call("file_tools", "read_file", True)
            
            tracker.complete_execution(True)
            
            assert tracker.metrics.success is True
            assert tracker.metrics.error_message is None
            assert tracker.metrics.execution_time_seconds is not None
            assert tracker.metrics.execution_time_seconds > 0
    
    def test_complete_execution_with_error(self):
        """Test completing execution with error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.start_execution("gpt-4", "team", "Test prompt")
            tracker.complete_execution(False, "Test error message")
            
            assert tracker.metrics.success is False
            assert tracker.metrics.error_message == "Test error message"
    
    def test_save_metrics(self):
        """Test saving metrics to JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.start_execution("gpt-4", "team", "Test prompt")
            tracker.add_agent("agent1", "worker")
            tracker.record_agent_response("agent1", 100)
            tracker.record_tool_call("file_tools", "read_file", True)
            tracker.complete_execution(True)
            
            filepath = tracker.save_metrics("test_metrics.json")
            
            assert os.path.exists(filepath)
            
            # Verify JSON content
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert data["model"] == "gpt-4"
            assert data["agents_mode"] == "team"
            assert data["prompt"] == "Test prompt"
            assert data["total_tokens"] == 100
            assert data["total_agent_responses"] == 1
            assert data["total_tool_calls"] == 1
            assert data["success"] is True
            assert "execution_time_seconds" in data
    
    def test_get_summary(self):
        """Test getting metrics summary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.start_execution("gpt-4", "team", "Test prompt")
            tracker.add_agent("agent1", "worker")
            tracker.record_agent_response("agent1", 100)
            tracker.record_tool_call("file_tools", "read_file", True)
            tracker.complete_execution(True)
            
            summary = tracker.get_summary()
            
            assert summary["model"] == "gpt-4"
            assert summary["agents_mode"] == "team"
            assert summary["total_tokens"] == 100
            assert summary["total_agent_responses"] == 1
            assert summary["total_tool_calls"] == 1
            assert summary["success"] is True
            assert "execution_time_seconds" in summary
    
    def test_record_initiator_chat_cut_short(self):
        """Test recording initiator chat cut short."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            assert tracker.metrics.initiator_chat_cut_short is False
            tracker.record_initiator_chat_cut_short()
            assert tracker.metrics.initiator_chat_cut_short is True
    
    def test_record_delegation_limit_reached(self):
        """Test recording delegation limit reached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            assert tracker.metrics.delegation_limit_reached is False
            tracker.record_delegation_limit_reached()
            assert tracker.metrics.delegation_limit_reached is True
    
    def test_record_delegation_chat_max_rounds_reached(self):
        """Test recording delegation chat max rounds reached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            assert tracker.metrics.delegation_chat_max_rounds_reached_count == 0
            tracker.record_delegation_chat_max_rounds_reached()
            assert tracker.metrics.delegation_chat_max_rounds_reached_count == 1
            tracker.record_delegation_chat_max_rounds_reached()
            assert tracker.metrics.delegation_chat_max_rounds_reached_count == 2
    
    def test_new_metrics_in_saved_json(self):
        """Test that new metrics are included in saved JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = MetricsTracker(temp_dir)
            
            tracker.start_execution("gpt-4", "team", "Test prompt")
            tracker.record_initiator_chat_cut_short()
            tracker.record_delegation_limit_reached()
            tracker.record_delegation_chat_max_rounds_reached()
            tracker.record_delegation_chat_max_rounds_reached()
            tracker.complete_execution(True)
            
            filepath = tracker.save_metrics("test_new_metrics.json")
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert data["initiator_chat_cut_short"] is True
            assert data["delegation_limit_reached"] is True
            assert data["delegation_chat_max_rounds_reached_count"] == 2


class TestExecutionMetrics:
    """Test cases for ExecutionMetrics dataclass."""
    
    def test_execution_metrics_creation(self):
        """Test ExecutionMetrics dataclass creation."""
        metrics = ExecutionMetrics(
            timestamp="2024-01-01T00:00:00",
            model="gpt-4",
            agents_mode="team",
            prompt="Test prompt",
            agents=[],
            tool_groups={},
            tool_functions={}
        )
        
        assert metrics.timestamp == "2024-01-01T00:00:00"
        assert metrics.model == "gpt-4"
        assert metrics.agents_mode == "team"
        assert metrics.prompt == "Test prompt"
        assert metrics.total_tokens == 0
        assert metrics.total_agent_responses == 0
        assert metrics.total_tool_calls == 0
        assert metrics.success is False
        assert metrics.initiator_chat_cut_short is False
        assert metrics.delegation_limit_reached is False
        assert metrics.delegation_chat_max_rounds_reached_count == 0


class TestAgentMetrics:
    """Test cases for AgentMetrics dataclass."""
    
    def test_agent_metrics_creation(self):
        """Test AgentMetrics dataclass creation."""
        metrics = AgentMetrics(
            agent_name="test_agent",
            agent_type="worker"
        )
        
        assert metrics.agent_name == "test_agent"
        assert metrics.agent_type == "worker"
        assert metrics.response_count == 0
        assert metrics.total_tokens == 0
        assert metrics.tool_calls == 0


class TestToolCallMetrics:
    """Test cases for ToolCallMetrics dataclass."""
    
    def test_tool_call_metrics_creation(self):
        """Test ToolCallMetrics dataclass creation."""
        metrics = ToolCallMetrics(
            tool_name="file_tools",
            tool_group="file",
            function_name="read_file"
        )
        
        assert metrics.tool_name == "file_tools"
        assert metrics.tool_group == "file"
        assert metrics.function_name == "read_file"
        assert metrics.call_count == 0
        assert metrics.success_count == 0
        assert metrics.error_count == 0 