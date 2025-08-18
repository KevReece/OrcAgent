#!/usr/bin/env python3
"""
Test Delegation Tracker Module

Integration tests for the delegation tracking functionality.
"""

import pytest
import tempfile
import os
from datetime import datetime
from metrics.delegation_tracker import DelegationTracker, DelegationNode


class TestDelegationTracker:
    """Test cases for DelegationTracker class."""
    
    def test_delegation_tracker_initialization(self):
        """Test DelegationTracker initialization."""
        tracker = DelegationTracker()
        
        assert tracker.root_delegations == []
        assert tracker.current_node is None
        assert tracker.delegation_stack == []
        assert not tracker.has_delegations()
    
    def test_start_delegation(self):
        """Test starting a delegation."""
        tracker = DelegationTracker()
        
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        
        assert len(tracker.root_delegations) == 1
        assert tracker.root_delegations[0].agent_name == "agent2"
        assert tracker.root_delegations[0].task_description == "Create a file"
        assert tracker.root_delegations[0].status == "pending"
        assert tracker.current_node == tracker.root_delegations[0]
        assert tracker.has_delegations()
    
    def test_nested_delegations(self):
        """Test nested delegations."""
        tracker = DelegationTracker()
        
        # Start first delegation
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        
        # Start nested delegation
        tracker.start_delegation("agent2", "agent3", "Write content", "2024-01-01T00:01:00")
        
        assert len(tracker.root_delegations) == 1
        assert len(tracker.root_delegations[0].children) == 1
        assert tracker.root_delegations[0].children[0].agent_name == "agent3"
        assert tracker.current_node.agent_name == "agent3"
    
    def test_complete_delegation(self):
        """Test completing a delegation."""
        tracker = DelegationTracker()
        
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        tracker.complete_delegation("agent2", "File created successfully", "2024-01-01T00:01:00")
        
        assert tracker.root_delegations[0].status == "completed"
        assert tracker.root_delegations[0].result == "File created successfully"
    
    def test_fail_delegation(self):
        """Test failing a delegation."""
        tracker = DelegationTracker()
        
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        tracker.fail_delegation("agent2", "Permission denied", "2024-01-01T00:01:00")
        
        assert tracker.root_delegations[0].status == "failed"
        assert "Permission denied" in tracker.root_delegations[0].result
    
    def test_end_delegation(self):
        """Test ending a delegation."""
        tracker = DelegationTracker()
        
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        tracker.start_delegation("agent2", "agent3", "Write content", "2024-01-01T00:01:00")
        
        # End the nested delegation
        tracker.end_delegation("agent3")
        
        assert tracker.current_node.agent_name == "agent2"
        assert len(tracker.delegation_stack) == 1
    
    def test_get_tree_string_no_delegations(self):
        """Test tree string when no delegations exist."""
        tracker = DelegationTracker()
        
        tree_string = tracker.get_tree_string()
        
        assert tree_string == "No delegations tracked"
    
    def test_get_tree_string_single_delegation(self):
        """Test tree string for a single delegation."""
        tracker = DelegationTracker()
        
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        tracker.complete_delegation("agent2", "File created successfully", "2024-01-01T00:01:00")
        
        tree_string = tracker.get_tree_string()
        
        assert "✅ agent2 - Create a file" in tree_string
    
    def test_get_tree_string_nested_delegations(self):
        """Test tree string for nested delegations."""
        tracker = DelegationTracker()
        
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        tracker.start_delegation("agent2", "agent3", "Write content", "2024-01-01T00:01:00")
        tracker.complete_delegation("agent3", "Content written", "2024-01-01T00:02:00")
        tracker.complete_delegation("agent2", "File created successfully", "2024-01-01T00:03:00")
        
        tree_string = tracker.get_tree_string()
        
        assert "✅ agent2" in tree_string
        assert "✅ agent3" in tree_string
        assert "└── " in tree_string
        # agent2 is the only root node, so we only see └── not ├──
    
    def test_save_delegation_tree(self):
        """Test saving delegation tree to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = DelegationTracker()
            
            tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
            tracker.complete_delegation("agent2", "File created successfully", "2024-01-01T00:01:00")
            
            filepath = os.path.join(temp_dir, "delegation_tree.txt")
            saved_filepath = tracker.save_delegation_tree(filepath)
            
            assert os.path.exists(saved_filepath)
            
            with open(saved_filepath, 'r') as f:
                content = f.read()
            
            assert "✅ agent2 - Create a file" in content
    
    def test_get_delegation_summary(self):
        """Test getting delegation summary."""
        tracker = DelegationTracker()
        
        # No delegations
        summary = tracker.get_delegation_summary()
        assert summary["total_delegations"] == 0
        assert summary["completed_delegations"] == 0
        assert summary["failed_delegations"] == 0
        assert summary["pending_delegations"] == 0
        assert not summary["has_delegations"]
        
        # Add some delegations
        tracker.start_delegation("agent1", "agent2", "Create a file", "2024-01-01T00:00:00")
        tracker.complete_delegation("agent2", "File created successfully", "2024-01-01T00:01:00")
        tracker.start_delegation("agent1", "agent3", "Read a file", "2024-01-01T00:02:00")
        tracker.fail_delegation("agent3", "File not found", "2024-01-01T00:03:00")
        
        summary = tracker.get_delegation_summary()
        assert summary["total_delegations"] == 2
        assert summary["completed_delegations"] == 1
        assert summary["failed_delegations"] == 1
        assert summary["pending_delegations"] == 0
        assert summary["has_delegations"]


class TestDelegationNode:
    """Test cases for DelegationNode dataclass."""
    
    def test_delegation_node_creation(self):
        """Test DelegationNode creation."""
        node = DelegationNode(
            agent_name="test_agent",
            task_description="Test task",
            status="pending"
        )
        
        assert node.agent_name == "test_agent"
        assert node.task_description == "Test task"
        assert node.status == "pending"
        assert node.children == []
        assert node.parent is None
        assert node.timestamp is None
        assert node.result is None 