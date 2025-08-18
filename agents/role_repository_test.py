#!/usr/bin/env python3

"""
Test module for RoleRepository class.
"""

import tempfile
import pytest
from unittest.mock import Mock, patch
from agents.entities import Role, Worker
from agents.role_repository import RoleRepository
from logger.log_wrapper import get_logger

logger = get_logger("test:role_repository", __name__)


class TestRoleRepository:
    """Test suite for RoleRepository class."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        # Reset singleton for clean testing
        RoleRepository.reset_singleton()
        # Reset worker counts for clean testing
        from agents.entities import reset_worker_counts
        reset_worker_counts()
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Clean up after each test."""
        # Reset singleton after each test
        RoleRepository.reset_singleton()
    
    def test_singleton_pattern(self):
        """Test that RoleRepository follows singleton pattern."""
        repo1 = RoleRepository()
        repo2 = RoleRepository()
        
        assert repo1 is repo2
    
    def test_initialization(self):
        """Test repository initialization."""
        repo = RoleRepository()
        repo.initialize(self.temp_dir, self.config_list, is_integration_test=True)
        
        assert repo._run_dir == self.temp_dir
        assert repo._config_list == self.config_list
        assert repo._is_integration_test == True
    
    def test_register_role(self):
        """Test registering a role in the repository."""
        repo = RoleRepository()
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        
        repo.register_role(role)
        
        assert repo.get_role("test_role") == role
        assert "test_role" in repo._roles_by_name
    
    def test_register_worker(self):
        """Test registering a worker in the repository."""
        repo = RoleRepository()
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        worker = Worker(role=role, worker_id=1)
        
        repo.register_worker(worker)
        
        assert repo.get_worker("test_role_1") == worker
        assert "test_role_1" in repo._workers_by_agent_name
    
    @patch('agent_environment.agent_environments.setup_agent_working_directories')
    @patch('importlib.import_module')
    def test_create_worker_basic(self, mock_import, mock_setup):
        """Test basic worker creation functionality."""
        # Mock the setup functions
        mock_setup.return_value = True
        mock_module = Mock()
        mock_module.get_tools.return_value = []
        mock_import.return_value = mock_module
        
        repo = RoleRepository()
        repo.initialize(self.temp_dir, self.config_list, is_integration_test=True)
        
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        repo.register_role(role)
        
        worker = repo.create_worker("test_role", is_initiator=True)
        
        assert worker.role == role
        assert worker.worker_id == 1
        assert worker.is_initiator == True
        assert repo.get_worker("test_role_1") == worker
        assert repo.get_worker_agent("test_role_1") is not None
        assert repo.get_worker_executor("test_role_1") is not None
    
    def test_create_worker_without_initialization(self):
        """Test that creating worker without initialization raises error."""
        repo = RoleRepository()
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        repo.register_role(role)
        
        with pytest.raises(ValueError, match="Repository not initialized"):
            repo.create_worker("test_role")
    
    def test_create_worker_role_not_found(self):
        """Test that creating worker with non-existent role raises error."""
        repo = RoleRepository()
        repo.initialize(self.temp_dir, self.config_list)
        
        with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
            repo.create_worker("nonexistent")
    
    def test_get_initial_worker(self):
        """Test getting the initial worker."""
        repo = RoleRepository()
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        
        worker1 = Worker(role=role, worker_id=1, is_initiator=False)
        worker2 = Worker(role=role, worker_id=2, is_initiator=True)
        
        repo.register_worker(worker1)
        repo.register_worker(worker2)
        
        initial_worker = repo.get_initial_worker()
        assert initial_worker == worker2
    
    def test_get_initial_worker_none(self):
        """Test getting initial worker when none exists."""
        repo = RoleRepository()
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        
        worker = Worker(role=role, worker_id=1, is_initiator=False)
        repo.register_worker(worker)
        
        initial_worker = repo.get_initial_worker()
        assert initial_worker is None
    
    def test_clear_repository(self):
        """Test clearing repository data."""
        repo = RoleRepository()
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        worker = Worker(role=role, worker_id=1)
        
        repo.register_role(role)
        repo.register_worker(worker)
        
        assert len(repo._roles_by_name) > 0
        assert len(repo._workers_by_agent_name) > 0
        
        repo.clear()
        
        assert len(repo._roles_by_name) == 0
        assert len(repo._workers_by_agent_name) == 0
    
    def test_get_all_methods(self):
        """Test getting all roles and workers."""
        repo = RoleRepository()
        role1 = Role(role_name="role1", base_instructions="Test1", description="Desc1")
        role2 = Role(role_name="role2", base_instructions="Test2", description="Desc2")
        worker1 = Worker(role=role1, worker_id=1)
        worker2 = Worker(role=role2, worker_id=1)
        
        repo.register_role(role1)
        repo.register_role(role2)
        repo.register_worker(worker1)
        repo.register_worker(worker2)
        
        all_roles = repo.get_all_roles()
        all_workers = repo.get_all_workers()
        
        assert len(all_roles) == 2
        assert role1 in all_roles
        assert role2 in all_roles
        
        assert len(all_workers) == 2
        assert worker1 in all_workers
        assert worker2 in all_workers
    
    def test_auto_generate_worker_id(self):
        """Test auto-generation of worker IDs."""
        repo = RoleRepository()
        repo.initialize(self.temp_dir, self.config_list, is_integration_test=True)
        
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        repo.register_role(role)
        
                # Mock the dependencies for create_worker
        with patch('agent_environment.agent_environments.setup_agent_working_directories') as mock_setup, \
             patch('importlib.import_module') as mock_import:
            mock_setup.return_value = True
            mock_module = Mock()
            mock_module.get_tools.return_value = []
            mock_import.return_value = mock_module

            # Create first worker - should get worker_id 1
            worker1 = repo.create_worker("test_role")
            assert worker1.worker_id == 1
            
            # Create second worker - should get worker_id 2 
            worker2 = repo.create_worker("test_role")
            assert worker2.worker_id == 2
    
    def test_create_worker_with_associates(self):
        """Test creating worker with associates."""
        repo = RoleRepository()
        repo.initialize(self.temp_dir, self.config_list, is_integration_test=True)
        
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        repo.register_role(role)
        
        associates = [("agent1", "relationship1"), ("agent2", "relationship2")]
        
                # Mock the dependencies for create_worker
        with patch('agent_environment.agent_environments.setup_agent_working_directories') as mock_setup, \
             patch('importlib.import_module') as mock_import:
            mock_setup.return_value = True
            mock_module = Mock()
            mock_module.get_tools.return_value = []
            mock_import.return_value = mock_module

            worker = repo.create_worker("test_role", associates=associates)
            
            assert len(worker._associates) == 2
            assert worker._associates[0].name == "agent1"
            assert worker._associates[0].relationship == "relationship1"
            assert worker._associates[1].name == "agent2"
            assert worker._associates[1].relationship == "relationship2" 