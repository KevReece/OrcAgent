#!/usr/bin/env python3

"""
Test module for initial agents with group chat support.
"""

import tempfile
from unittest.mock import Mock, patch
import autogen  # type: ignore
from agents.initial_agents import (
    create_and_configure_agents,
    _create_user_proxy_agent
)
from logger.log_wrapper import get_logger

logger = get_logger("test:initial_agents", __name__)

class TestAgentCreation:
    """Test suite for agent creation functions."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Cleanup after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_user_proxy_agent(self):
        """Test creation of user proxy agent."""
        agent = _create_user_proxy_agent()
        
        assert isinstance(agent, autogen.UserProxyAgent)
        assert agent.name == "root_initiator"
        assert agent.human_input_mode == "NEVER"
        assert agent.max_consecutive_auto_reply() == 0
    
class TestGroupChatSetup:
    """Test suite for group chat setup functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
        # Reset worker counts to ensure consistent naming
        from agents.entities.worker import reset_worker_counts
        reset_worker_counts()
        # Reset role repository singleton to ensure clean state
        from agents.role_repository import RoleRepository
        RoleRepository.reset_singleton()
        self.agent_configs = [
            {
                "baseInstructions": "You are a test agent 1",
                "roleName": "test_role_1",
                "workerId": 1,
                "toolGroupNames": []
            },
            {
                "baseInstructions": "You are a test agent 2",
                "roleName": "test_role_2",
                "workerId": 1,
                "toolGroupNames": []
            }
        ]
    
    def teardown_method(self):
        """Cleanup after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('agents.definitions.team_definition.setup_default_repository')
    @patch('agents.initial_agents._create_user_proxy_agent')
    def test_create_and_configure_agents(self, mock_user_proxy, mock_setup_repo):
        """Test creation and configuration of agents."""
        # Mock setup with real AutoGen agents
        mock_repo = Mock()
        mock_worker = Mock()
        mock_worker.get_name.return_value = "general_manager_1"
        mock_repo.get_initial_worker.return_value = mock_worker
        
        # Create real autogen agents for proper validation
        mock_worker_agent = autogen.AssistantAgent(
            name="general_manager_1",
            system_message="Test agent",
            llm_config={"config_list": self.config_list}
        )
        mock_worker_executor = autogen.UserProxyAgent(
            name="general_manager_1_executor",
            system_message="Test executor",
            human_input_mode="NEVER",
            code_execution_config=False
        )
        
        mock_repo.get_worker_agent.return_value = mock_worker_agent
        mock_repo.get_worker_executor.return_value = mock_worker_executor
        mock_setup_repo.return_value = mock_repo
        
        mock_root_agent = autogen.UserProxyAgent(
            name="user_proxy",
            system_message="Test root",
            human_input_mode="NEVER",
            code_execution_config=False
        )
        mock_user_proxy.return_value = mock_root_agent
        
        manager, group_chat, root_agent = create_and_configure_agents(
            self.temp_dir, 
            self.config_list
        )
        
        assert root_agent == mock_root_agent
        assert manager is not None
        assert group_chat is not None
        assert len(group_chat.agents) == 2  # worker + executor
        
        mock_setup_repo.assert_called_once_with(
            self.temp_dir, 
            self.config_list, 
            is_integration_test=False
        ) 

    def test_create_and_configure_agents_solo(self):
        manager, group_chat, root_agent = create_and_configure_agents(
            self.temp_dir,
            self.config_list,
            mode="solo"
        )
        assert root_agent is not None
        assert manager is not None
        assert group_chat is not None
        assert len(group_chat.agents) == 2  # worker + executor
        agent_names = {agent.name for agent in group_chat.agents}
        assert any("solo_founder" in name for name in agent_names)
        assert any("executor" in name for name in agent_names)

    def test_create_and_configure_agents_pair(self):
        manager, group_chat, root_agent = create_and_configure_agents(
            self.temp_dir,
            self.config_list,
            mode="pair"
        )
        assert root_agent is not None
        assert manager is not None
        assert group_chat is not None
        assert len(group_chat.agents) == 2  # founder_ceo + founder_cto
        agent_names = {agent.name for agent in group_chat.agents}
        assert any("founder_ceo" in name for name in agent_names)
        assert any("executor" in name for name in agent_names)

    def test_create_and_configure_agents_orchestrator(self):
        manager, group_chat, root_agent = create_and_configure_agents(
            self.temp_dir,
            self.config_list,
            mode="orchestrator"
        )
        assert root_agent is not None
        assert manager is not None
        assert group_chat is not None
        assert len(group_chat.agents) == 2  # worker + executor
        agent_names = {agent.name for agent in group_chat.agents}
        assert any("orchestrator" in name for name in agent_names)
        assert any("executor" in name for name in agent_names)

    def test_create_and_configure_agents_company(self):
        manager, group_chat, root_agent = create_and_configure_agents(
            self.temp_dir,
            self.config_list,
            mode="company"
        )
        assert root_agent is not None
        assert manager is not None
        assert group_chat is not None
        assert len(group_chat.agents) == 2  # CEO worker + executor
        agent_names = {agent.name for agent in group_chat.agents}
        assert any("ceo" in name for name in agent_names)
        assert any("executor" in name for name in agent_names) 