#!/usr/bin/env python3
"""
Test module for memory tools.
"""

import unittest
import tempfile
import shutil
from tools.memory_tools import Memory, MemoryEntry, get_tools
from tools.context import ToolsContext
from agents.role_repository import RoleRepository
from agents.entities.role import Role
from agents.entities.worker import Worker


class TestMemoryEntry(unittest.TestCase):
    """Test suite for MemoryEntry class."""
    
    def test_memory_entry_creation(self):
        """Test creation of MemoryEntry."""
        entry = MemoryEntry("test content", 5)
        self.assertEqual(entry.content, "test content")
        self.assertEqual(entry.priority, 5)
    
    def test_memory_entry_comparison(self):
        """Test comparison of MemoryEntry objects (for heap ordering)."""
        entry1 = MemoryEntry("low priority", 1)
        entry2 = MemoryEntry("high priority", 10)
        
        # Lower priority should be "less than" for min heap behavior
        self.assertTrue(entry1 < entry2)
        self.assertFalse(entry2 < entry1)


class TestMemory(unittest.TestCase):
    """Test suite for Memory class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.memory = Memory(max_size=3)  # Small size for easier testing
    
    def test_memory_initialization(self):
        """Test Memory initialization."""
        self.assertEqual(self.memory.max_size, 3)
        self.assertEqual(self.memory.get_memory_count(), 0)
        self.assertEqual(self.memory.get_memories(), [])
    
    def test_store_memory_success(self):
        """Test successful memory storage."""
        result = self.memory.store_memory("Important task", 5)
        self.assertIn("Successfully stored", result)
        self.assertEqual(self.memory.get_memory_count(), 1)
    
    def test_store_empty_memory(self):
        """Test storing empty memory content."""
        result = self.memory.store_memory("", 5)
        self.assertIn("Error: Memory content cannot be empty", result)
        
        result = self.memory.store_memory("   ", 5)
        self.assertIn("Error: Memory content cannot be empty", result)
    
    def test_store_memory_truncation(self):
        """Test memory content truncation for long content."""
        long_content = "a" * 1500  # Longer than 1000 character limit
        result = self.memory.store_memory(long_content, 5)
        self.assertIn("Successfully stored", result)
        
        memories = self.memory.get_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(len(memories[0][0]), 1000)  # Should be truncated
    
    def test_memory_priority_ordering(self):
        """Test that memories are returned in priority order."""
        self.memory.store_memory("Low priority", 1)
        self.memory.store_memory("High priority", 10)
        self.memory.store_memory("Medium priority", 5)
        
        memories = self.memory.get_memories()
        self.assertEqual(len(memories), 3)
        
        # Should be ordered by priority (highest first)
        self.assertEqual(memories[0][1], 10)  # High priority
        self.assertEqual(memories[1][1], 5)   # Medium priority
        self.assertEqual(memories[2][1], 1)   # Low priority
    
    def test_memory_max_size_enforcement(self):
        """Test that memory enforces max size limit."""
        # Fill memory to max capacity
        self.memory.store_memory("Memory 1", 1)
        self.memory.store_memory("Memory 2", 2)
        self.memory.store_memory("Memory 3", 3)
        self.assertEqual(self.memory.get_memory_count(), 3)
        
        # Add higher priority memory - should replace lowest priority
        result = self.memory.store_memory("High priority memory", 10)
        self.assertIn("Successfully stored", result)
        self.assertEqual(self.memory.get_memory_count(), 3)
        
        memories = self.memory.get_memories()
        priorities = [mem[1] for mem in memories]
        self.assertIn(10, priorities)  # New high priority should be included
        self.assertNotIn(1, priorities)  # Lowest priority should be removed
    
    def test_memory_below_threshold_rejection(self):
        """Test that memories with too low priority are rejected when at capacity."""
        # Fill memory with higher priority items
        self.memory.store_memory("Memory 1", 5)
        self.memory.store_memory("Memory 2", 6)
        self.memory.store_memory("Memory 3", 7)
        
        # Try to add lower priority memory
        result = self.memory.store_memory("Low priority", 2)
        self.assertIn("not stored", result)
        self.assertIn("below current minimum", result)
        self.assertEqual(self.memory.get_memory_count(), 3)
    
    def test_memory_clear(self):
        """Test clearing all memories."""
        self.memory.store_memory("Test memory", 5)
        self.assertEqual(self.memory.get_memory_count(), 1)
        
        self.memory.clear()
        self.assertEqual(self.memory.get_memory_count(), 0)
        self.assertEqual(self.memory.get_memories(), [])


class TestMemoryTools(unittest.TestCase):
    """Test suite for memory tools integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Set up a minimal role repository and worker for memory tools
        self.role_repository = RoleRepository()
        self.role_repository.initialize(
            run_dir=self.temp_dir,
            config_list=[{"model": "test-model"}],
            is_integration_test=True
        )
        # Use unique names to avoid collisions
        self.role_name = f"test_memory_role_{id(self)}"
        self.worker_name = f"{self.role_name}_1"
        role = Role(
            role_name=self.role_name,
            base_instructions="You are a memory test role.",
            description="Role for memory tools integration test.",
            role_version=1,
            tool_group_names=[]
        )
        self.role_repository.register_role(role)
        worker = Worker(role=role, worker_id=1)
        worker.initialize_runtime_config(
            run_dir=self.temp_dir,
            config_list=[{"model": "test-model"}],
            is_integration_test=True,
            role_repository=self.role_repository
        )
        self.role_repository.register_worker(worker)
        tools_context = ToolsContext(
            role_repository=self.role_repository,
            self_worker_name=self.worker_name,
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        tools = get_tools(tools_context)
        class Self:
            def __init__(self, tools):
                self.store_memory = tools[0]
                self.get_memories = tools[1]
        self.memory_tools = Self(tools)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset the RoleRepository singleton for isolation
        if hasattr(self.role_repository, 'reset_singleton'):
            self.role_repository.reset_singleton()
    
    def test_store_and_get_memories_tools(self):
        """Test store_memory and get_memories tool functions."""
        # Store some memories
        result1 = self.memory_tools.store_memory("First task", 5)
        result2 = self.memory_tools.store_memory("Important deadline", 10)
        result3 = self.memory_tools.store_memory("Low priority note", 1)
        
        self.assertIn("Successfully stored", result1)
        self.assertIn("Successfully stored", result2)
        self.assertIn("Successfully stored", result3)
        
        # Get memories
        memories = self.memory_tools.get_memories()
        self.assertEqual(len(memories), 3)
        
        # Verify ordering (highest priority first)
        self.assertEqual(memories[0][1], 10)  # Important deadline
        self.assertEqual(memories[1][1], 5)   # First task
        self.assertEqual(memories[2][1], 1)   # Low priority note
    
    def test_memory_tools_error_handling(self):
        """Test error handling in memory tools."""
        result = self.memory_tools.store_memory("", 5)
        self.assertIn("Error", result)
        
        # Should still return empty list for get_memories
        memories = self.memory_tools.get_memories()
        self.assertEqual(memories, [])
    
    def test_memory_tools_capacity_management(self):
        """Test that memory tools properly manage capacity."""
        # Store many memories to test capacity management
        for i in range(150):  # More than default capacity of 100
            self.memory_tools.store_memory(f"Memory {i}", i)
        
        memories = self.memory_tools.get_memories()
        self.assertLessEqual(len(memories), 100)  # Should not exceed capacity
        
        # Should keep highest priority memories
        if memories:
            self.assertGreaterEqual(memories[0][1], 50)  # High priority should be retained


if __name__ == '__main__':
    unittest.main() 