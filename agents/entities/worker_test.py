#!/usr/bin/env python3

"""
Test module for Worker entity class.
"""

import pytest
import tempfile
import shutil
from agents.entities import Role, Worker, Associate, reset_worker_counts, get_worker_count
from logger.log_wrapper import get_logger

logger = get_logger("test:entities:worker", __name__)


class TestWorker:
    """Test suite for Worker class."""
    
    def setup_method(self):
        """Set up test role for worker tests and reset worker counts."""
        reset_worker_counts()  # Ensure clean state for each test
        self.test_role = Role(
            role_name="test_role",
            base_instructions="Test instructions",
            description="Test description"
        )
    
    def test_worker_creation_minimal_auto_id(self):
        """Test creation of Worker with auto-incrementing ID."""
        worker1 = Worker(role=self.test_role)
        worker2 = Worker(role=self.test_role)
        
        assert worker1.role == self.test_role
        assert worker1.worker_id == 1
        assert worker1._associates == []
        assert worker1.is_initiator == False
        assert worker1.memory is not None
        assert worker1.memory.get_memory_count() == 0
        
        assert worker2.worker_id == 2
        assert worker2.role == self.test_role
    
    def test_worker_creation_explicit_id(self):
        """Test creation of Worker with explicit ID."""
        worker = Worker(role=self.test_role, worker_id=5)
        
        assert worker.role == self.test_role
        assert worker.worker_id == 5
        assert worker._associates == []
        assert worker.is_initiator == False
        assert worker.memory is not None
    
    def test_worker_creation_full(self):
        """Test creation of Worker with all fields specified."""
        associates = [Associate("agent1", "relationship1")]
        
        worker = Worker(
            role=self.test_role,
            worker_id=3,
            is_initiator=True
        )
        worker.set_associates(associates)
        
        assert worker.role == self.test_role
        assert worker.worker_id == 3
        assert len(worker._associates) == 1
        assert worker._associates[0].name == "agent1"
        assert worker.is_initiator == True
        assert worker.memory is not None
    
    def test_auto_incrementing_ids_per_role(self):
        """Test that worker IDs auto-increment separately per role."""
        role2 = Role(
            role_name="other_role",
            base_instructions="Other instructions",
            description="Other description"
        )
        
        # Create workers for first role
        worker1_role1 = Worker(role=self.test_role)
        worker2_role1 = Worker(role=self.test_role)
        
        # Create workers for second role  
        worker1_role2 = Worker(role=role2)
        worker2_role2 = Worker(role=role2)
        
        # Workers for same role should increment
        assert worker1_role1.worker_id == 1
        assert worker2_role1.worker_id == 2
        
        # Workers for different role should start fresh
        assert worker1_role2.worker_id == 1
        assert worker2_role2.worker_id == 2
        
        assert get_worker_count("test_role") == 2
        assert get_worker_count("other_role") == 2
    
    def test_worker_validation_invalid_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="role must be a Role instance"):
            Worker(role="not_a_role")
    
    def test_worker_validation_invalid_worker_id(self):
        """Test that invalid worker_id raises ValueError."""
        with pytest.raises(ValueError, match="worker_id must be >= 1"):
            Worker(role=self.test_role, worker_id=0)
        
        with pytest.raises(ValueError, match="worker_id must be >= 1"):
            Worker(role=self.test_role, worker_id=-1)
    
    def test_get_name(self):
        """Test worker name generation."""
        worker = Worker(role=self.test_role, worker_id=5)
        assert worker.get_name() == "test_role_5"
    
    def test_get_name_auto_id(self):
        """Test worker name generation with auto-incrementing ID."""
        worker = Worker(role=self.test_role)
        assert worker.get_name() == "test_role_1"
    
    def test_memory_functionality(self):
        """Test worker memory storage and retrieval."""
        worker = Worker(role=self.test_role)
        
        # Test storing memories
        result1 = worker.store_memory("Important task", 10)
        result2 = worker.store_memory("Medium priority note", 5)
        result3 = worker.store_memory("Low priority reminder", 1)
        
        assert "Successfully stored" in result1
        assert "Successfully stored" in result2
        assert "Successfully stored" in result3
        
        # Test retrieving memories
        memories = worker.get_memories()
        assert len(memories) == 3
        
        # Should be ordered by priority (highest first)
        assert memories[0][1] == 10  # Important task
        assert memories[1][1] == 5   # Medium priority
        assert memories[2][1] == 1   # Low priority
    
    def test_clear_agents_on_memory_update(self):
        """Test that agents are cleared when memory is updated."""
        worker = Worker(role=self.test_role)
        
        # Set mock agents
        worker._worker_agent = "mock_agent"
        worker._executor_agent = "mock_executor"
        
        # Store memory should clear agents
        worker.store_memory("Test memory", 5)
        
        assert worker._worker_agent is None
        assert worker._executor_agent is None
    
    def test_initialize_runtime_config(self):
        """Test initializing worker with runtime configuration."""
        worker = Worker(role=self.test_role)
        temp_dir = tempfile.mkdtemp()
        config_list = [{"model": "test", "api_key": "test"}]
        
        try:
            worker.initialize_runtime_config(temp_dir, config_list, True)
            
            assert worker._run_dir == temp_dir
            assert worker._config_list == config_list
            assert worker._is_integration_test == True
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_custom_instructions_with_memory(self):
        """Test that custom instructions include memory information."""
        worker = Worker(role=self.test_role)
        
        # Add some memories
        worker.store_memory("Important context", 10)
        worker.store_memory("Background info", 5)
        
        instructions = worker.get_custom_instructions()
        
        assert "Test instructions" in instructions  # Base instructions
        assert "Memories:" in instructions
        assert "Priority 10: Important context" in instructions
        assert "Priority 5: Background info" in instructions
    
    def test_worker_clone_default(self):
        """Test cloning a worker with default parameters."""
        original = Worker(
            role=self.test_role,
            worker_id=3,
            is_initiator=True
        )
        original.set_associates([Associate("agent1", "relationship1")])
        
        clone = original.clone()
        
        # Should be identical but separate instances
        assert clone.role == original.role
        assert clone.worker_id != original.worker_id  # Auto-assigned new ID
        assert len(clone._associates) == len(original._associates)
        assert clone._associates[0].name == original._associates[0].name
        assert clone._associates is not original._associates  # Different list objects
        assert clone.is_initiator == False  # Clones are not initiators by default
        assert clone.memory is not original.memory  # Different memory instances
    
    def test_worker_clone_with_modifications(self):
        """Test cloning a worker with modifications."""
        new_role = Role(role_name="new_role", base_instructions="New instructions", description="New desc")
        original = Worker(role=self.test_role, worker_id=1)
        
        clone = original.clone(new_worker_id=5, new_role=new_role)
        
        assert clone.role == new_role
        assert clone.worker_id == 5
        assert original.role == self.test_role  # Original unchanged
        assert original.worker_id == 1  # Original unchanged
    
    def test_str_representation(self):
        """Test string representation of Worker."""
        worker = Worker(role=self.test_role, worker_id=3)
        
        result = str(worker)
        expected = "Worker(test_role, worker_3, 0 memories)"
        
        assert result == expected
    
    def test_str_representation_with_initiator_and_memories(self):
        """Test string representation of Worker with initiator flag and memories."""
        worker = Worker(role=self.test_role, worker_id=3, is_initiator=True)
        worker.store_memory("Test memory", 5)
        
        result = str(worker)
        expected = "Worker(test_role, worker_3 (initiator), 1 memories)"
        
        assert result == expected
    
    def test_repr_representation(self):
        """Test detailed string representation of Worker."""
        worker = Worker(
            role=self.test_role,
            worker_id=3,
            is_initiator=True
        )
        worker.set_associates([Associate("agent1", "relationship1")])
        worker.store_memory("Test memory", 5)
        
        result = repr(worker)
        expected = "Worker(role='test_role', worker_id=3, associates=1, is_initiator=True, memories=1)"
        
        assert result == expected
    
    def test_lazy_agent_creation_error_handling(self):
        """Test that lazy agent creation handles missing runtime config properly."""
        worker = Worker(role=self.test_role)
        
        # Should raise error when trying to create agents without runtime config
        with pytest.raises(ValueError, match="Worker not initialized with runtime config"):
            worker.get_worker_agent()
        
        with pytest.raises(ValueError, match="Worker not initialized with runtime config"):
            worker.get_executor_agent()
    
    def test_memory_tools_integration(self):
        """Test that memory tools work with worker's memory when used as regular tools."""
        from tools.memory_tools import get_tools
        from tools.context import ToolsContext
        
        worker = Worker(role=self.test_role)
        
        # Create a mock tools context
        mock_repo = type('MockRepo', (), {
            'get_worker': lambda self, name: worker if name == worker.get_name() else None
        })()
        tools_context = ToolsContext(
            role_repository=mock_repo,
            self_worker_name=worker.get_name(),
            agent_work_dir="/tmp",
            is_integration_test=True
        )
        
        # Test memory tools with worker memory methods
        memory_tools = get_tools(tools_context)
        
        assert len(memory_tools) == 2
        store_memory_tool = memory_tools[0]
        get_memories_tool = memory_tools[1]
        
        # Store memories using the tool
        result1 = store_memory_tool("Important task", 10)
        result2 = store_memory_tool("Low priority note", 1)
        
        assert "Successfully stored" in result1
        assert "Successfully stored" in result2
        
        # Get memories using the tool
        memories = get_memories_tool()
        assert len(memories) == 2
        assert memories[0][1] == 10  # Higher priority first
        assert memories[1][1] == 1
        
        # Verify that worker's memory actually contains the memories
        worker_memories = worker.get_memories()
        assert len(worker_memories) == 2
        assert worker_memories == memories
    
    def test_reset_worker_counts(self):
        """Test resetting worker counts."""
        # Create some workers to increment counts
        Worker(role=self.test_role)
        Worker(role=self.test_role)
        
        assert get_worker_count("test_role") == 2
        
        # Reset counts
        reset_worker_counts()
        
        assert get_worker_count("test_role") == 0
        
        # New workers should start from 1 again
        new_worker = Worker(role=self.test_role)
        assert new_worker.worker_id == 1 