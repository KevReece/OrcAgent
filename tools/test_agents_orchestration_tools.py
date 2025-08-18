#!/usr/bin/env python3
"""
Test Agents Orchestration Tools

This module tests the agents orchestration tools functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from agents.role_repository import RoleRepository
from agents.entities import Role, Worker, Associate
from tools.agents_orchestration_tools import get_tools
from tools.context import ToolsContext
import json


class TestAgentsOrchestrationTools:
    """Test the AgentsOrchestrationTools class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset singleton to ensure clean state
        RoleRepository.reset_singleton()
        
        # Reset worker counts
        from agents.entities.worker import reset_worker_counts
        reset_worker_counts()
        
        self.temp_dir = tempfile.mkdtemp()
        self.role_repository = RoleRepository()
        self.role_repository.initialize(
            run_dir=self.temp_dir,
            config_list=[{"model": "test-model"}],
            is_integration_test=True
        )
        self.tools_context = ToolsContext(
            role_repository=self.role_repository,
            self_worker_name=None,
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        (
            self.create_worker,
            self.define_role,
            self.get_role,
            self.get_role_version,
            self.get_worker,
            self.delete_worker,
            self.add_worker_associate
        ) = get_tools(self.tools_context)
        
        # Create a test role
        self.test_role = Role(
            role_name="TestRole",
            base_instructions="You are a test role.",
            description="A test role for testing",
            role_version=1,
            tool_group_names=["file_tools"]
        )
        self.role_repository.register_role(self.test_role)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        RoleRepository.reset_singleton()
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_create_worker_success(self):
        """Test successful worker creation."""
        result = self.create_worker("TestRole")
        
        assert "Successfully created worker" in result
        assert "TestRole_1" in result
        assert "version 1" in result
        
        # Verify worker was created in repository
        worker = self.role_repository.get_worker("TestRole_1")
        assert worker is not None
        assert worker.role.role_name == "TestRole"
        assert worker.role.role_version == 1
    
    def test_create_worker_with_associates(self):
        """Test worker creation with associates."""
        # Create a second worker first
        result1 = self.create_worker("TestRole")
        
        # Create worker with associates
        associates = [("TestRole_1", "colleague")]
        result2 = self.create_worker("TestRole", associates=json.dumps(associates))
        
        assert "Successfully created worker" in result2
        
        # Verify worker was created
        worker = self.role_repository.get_worker("TestRole_2")
        assert worker is not None
        assert len(worker._associates) == 1
        assert worker._associates[0].name == "TestRole_1"
        
        # Verify associated_from was updated
        associate_worker = self.role_repository.get_worker("TestRole_1")
        assert associate_worker is not None
        assert "TestRole_2" in associate_worker._associated_from
    
    def test_create_worker_role_not_found(self):
        """Test worker creation with non-existent role."""
        result = self.create_worker("non_existent_role")
        
        assert "Error: Role 'non_existent_role' not found" in result
    
    def test_define_role_success(self):
        """Test successful role definition with a Python list of tool groups."""
        result = self.define_role(
            role_name="NewRole",
            base_instructions="You are a new role.",
            description="A new role for testing",
            tool_group_names=["file_tools", "git_tools"]
        )
        
        assert "Successfully defined role 'NewRole' version 1" in result
        
        # Verify role was created
        role = self.role_repository.get_role("NewRole")
        assert role is not None
        assert role.role_name == "NewRole"
        assert role.role_version == 1
        assert role.base_instructions == "You are a new role."
        assert len(role.tool_group_names) == 4  # file_tools, git_tools, delegation_tools, memory_tools
    
    def test_define_role_version_increment(self):
        """Test role definition with version increment when using Python list for tool groups."""
        # Define role first time
        self.define_role(
            role_name="VersionedRole",
            base_instructions="First version",
            description="A versioned role",
            tool_group_names=["file_tools"]
        )
        
        # Define role second time
        result = self.define_role(
            role_name="VersionedRole",
            base_instructions="Second version",
            description="A versioned role updated",
            tool_group_names=["file_tools"]
        )
        
        assert "Successfully defined role 'VersionedRole' version 2" in result
        
        # Verify role was updated
        role = self.role_repository.get_role("VersionedRole")
        assert role is not None
        assert role.role_version == 2
        assert role.base_instructions == "Second version"
    
    def test_get_role_success(self):
        """Test successful role retrieval."""
        result = self.get_role("TestRole")
        
        assert "Role 'TestRole' (version 1)" in result
        assert "A test role for testing" in result
        assert "file_tools" in result
        assert "You are a test role." in result
    
    def test_get_role_not_found(self):
        """Test role retrieval for non-existent role."""
        result = self.get_role("non_existent_role")
        
        assert "Error: Role 'non_existent_role' not found" in result
    
    def test_get_role_version_success(self):
        """Test successful role version retrieval."""
        result = self.get_role_version("TestRole", 1)
        
        assert "Role 'TestRole' (version 1)" in result
        assert "A test role for testing" in result
    
    def test_get_role_version_not_found(self):
        """Test role version retrieval for non-existent version on existing role."""
        # Use existing role created in setup: TestRole (version 1)
        result = self.get_role_version("TestRole", 2)
        
        assert "Error: Role 'TestRole' version 2 not found" in result
    
    def test_get_worker_success(self):
        """Test successful worker retrieval."""
        # Create a worker first
        self.create_worker("TestRole")
        
        result = self.get_worker("TestRole_1")
        
        assert "Worker 'TestRole_1'" in result
        assert "Role: TestRole (version 1)" in result
        assert "Worker ID: 1" in result
        assert "Is Initiator: False" in result
        assert "Associates: 0" in result
        assert "Associated From: 0 workers" in result
        assert "Memories: 0" in result
    
    def test_get_worker_not_found(self):
        """Test worker retrieval for non-existent worker."""
        result = self.get_worker("non_existent_worker")
        
        assert "Error: Worker 'non_existent_worker' not found" in result
    
    def test_delete_worker_success(self):
        """Test successful worker deletion."""
        # Create workers with associations
        self.create_worker("TestRole")
        associates = [("TestRole_1", "colleague")]
        self.create_worker("TestRole", associates=json.dumps(associates))
        
        # Verify association was created
        worker1 = self.role_repository.get_worker("TestRole_1")
        assert worker1 is not None
        worker2 = self.role_repository.get_worker("TestRole_2")
        assert worker2 is not None
        assert len(worker2._associates) == 1
        
        # Delete worker
        result = self.delete_worker("TestRole_2")
        assert "Successfully deleted worker 'TestRole_2'" in result
        
        # Verify worker was deleted
        deleted_worker = self.role_repository.get_worker("TestRole_2")
        assert deleted_worker is None
        
        # Verify association was cleaned up
        remaining_worker = self.role_repository.get_worker("TestRole_1")
        assert remaining_worker is not None
        assert "TestRole_2" not in remaining_worker._associated_from
    
    def test_delete_worker_not_found(self):
        """Test worker deletion for non-existent worker."""
        result = self.delete_worker("non_existent_worker")
        
        assert "Error: Worker 'non_existent_worker' not found" in result


class TestGetTools:
    """Test the get_tools function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.role_repository = RoleRepository()
        self.role_repository.initialize(
            run_dir=self.temp_dir,
            config_list=[{"model": "test-model"}],
            is_integration_test=True
        )
        self.tools_context = ToolsContext(
            role_repository=self.role_repository,
            self_worker_name=None,
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        RoleRepository.reset_singleton()
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_get_tools_success(self):
        """Test successful tool creation."""
        tools = get_tools(self.tools_context)
        assert len(tools) == 7
        tool_names = [tool.__name__ for tool in tools]
        expected_names = [
            'create_worker',
            'define_role', 
            'get_role',
            'get_role_version',
            'get_worker',
            'delete_worker',
            'add_worker_associate'
        ]
        for expected_name in expected_names:
            assert expected_name in tool_names
    
    def test_get_tools_no_repository(self):
        """Test tool creation without repository."""
        tools_context = ToolsContext(
            role_repository=None,
            self_worker_name=None,
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        tools = get_tools(tools_context)
        assert len(tools) == 0
    
    def test_create_worker_with_json_associates(self):
        """Test create_worker with JSON associates parameter."""
        tools = get_tools(self.tools_context)
        # Find the create_worker tool
        create_worker_tool = None
        for tool in tools:
            if tool.__name__ == 'create_worker':
                create_worker_tool = tool
                break
        assert create_worker_tool is not None
        # Test with valid JSON
        import json
        associates_json = json.dumps([("test_worker", "colleague")])
        # Mock the role repository to avoid actual worker creation
        with patch.object(self.role_repository, 'get_role') as mock_get_role:
            mock_role = Mock()
            mock_role.role_name = "test_role"
            mock_role.role_version = 1
            mock_get_role.return_value = mock_role
            with patch.object(self.role_repository, 'create_worker') as mock_create_worker:
                mock_worker = Mock()
                mock_worker.get_name.return_value = "test_role_1"
                mock_create_worker.return_value = mock_worker
                result = create_worker_tool("test_role", associates=associates_json)
                assert "Successfully created worker" in result
    
    def test_create_worker_with_invalid_json_associates(self):
        """Test create_worker with invalid JSON associates parameter."""
        tools = get_tools(self.tools_context)
        
        # Find the create_worker tool
        create_worker_tool = None
        for tool in tools:
            if tool.__name__ == 'create_worker':
                create_worker_tool = tool
                break
        
        assert create_worker_tool is not None
        
        # Test with invalid JSON
        result = create_worker_tool("test_role", associates="invalid json")
        
        assert "Error parsing associates JSON" in result
    
    def test_define_role_with_list_tool_groups(self):
        """Test define_role with Python list tool_group_names parameter."""
        tools = get_tools(self.tools_context)
        
        # Find the define_role tool
        define_role_tool = None
        for tool in tools:
            if tool.__name__ == 'define_role':
                define_role_tool = tool
                break
        
        assert define_role_tool is not None
        
        # Test with valid Python list
        result = define_role_tool(
            "NewRole",
            "You are a new role.",
            "A new role for testing",
            tool_group_names=["file_tools", "git_tools"]
        )
        
        assert "Successfully defined role 'NewRole' version 1" in result
        
        # Verify role was actually created
        role = self.role_repository.get_role("NewRole")
        assert role is not None
        assert role.role_name == "NewRole"
    
    def test_define_role_with_invalid_tool_groups(self):
        """Test define_role with invalid tool_group_names parameter types."""
        tools = get_tools(self.tools_context)
        
        # Find the define_role tool
        define_role_tool = None
        for tool in tools:
            if tool.__name__ == 'define_role':
                define_role_tool = tool
                break
        
        assert define_role_tool is not None
        
        # Test with invalid types
        result = define_role_tool(
            "new_role",
            "You are a new role.",
            "A new role for testing",
            tool_group_names="invalid type"
        )
        
        assert "Error: tool_group_names must be a non-empty list of strings" in result 