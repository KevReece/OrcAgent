#!/usr/bin/env python3
"""
Test module for delegation tools.
"""

import tempfile
from unittest.mock import Mock, patch
from tools.delegation_tools import DelegationTools, get_tools
from logger.log_wrapper import get_logger

logger = get_logger("test:delegation_tools", __name__)


class TestDelegationTools:
    """Test suite for delegation tools functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock agents
        self.mock_self_agent = Mock()
        self.mock_self_agent.name = "senior_architect_1"
        self.mock_self_agent.llm_config = {"config_list": [{"model": "gpt-4.1-nano", "api_key": "test"}]}
        
        self.mock_target_agent = Mock()
        self.mock_target_agent.name = "systems_engineer_1"
        self.mock_target_agent.llm_config = {"config_list": [{"model": "gpt-4.1-nano", "api_key": "test"}]}
        
        self.mock_self_executor = Mock()
        self.mock_self_executor.name = "senior_architect_1_executor"
        
        self.mock_target_executor = Mock()
        self.mock_target_executor.name = "systems_engineer_1_executor"
        
        # Create mock worker
        self.mock_target_worker = Mock()
        self.mock_target_worker.get_name.return_value = "systems_engineer"
        self.mock_target_worker.get_worker_agent.return_value = self.mock_target_agent
        self.mock_target_worker.get_executor_agent.return_value = self.mock_target_executor
        
        # Create mock role repository  
        self.mock_role_repository = Mock()
        self.mock_role_repository.get_worker.return_value = self.mock_target_worker
        self.mock_role_repository.get_all_workers.return_value = [self.mock_target_worker]
        self.mock_role_repository.get_worker_agent.return_value = self.mock_self_agent
        
        # Create delegation tools instance
        from tools.context import ToolsContext
        tools_context = ToolsContext(
            role_repository=self.mock_role_repository,
            self_worker_name=self.mock_self_agent.name,
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        self.delegation_tools = DelegationTools(tools_context)
    
    def teardown_method(self):
        """Cleanup after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('autogen.GroupChat')
    @patch('autogen.GroupChatManager')
    def test_delegate_to_worker_success(self, mock_group_chat_manager, mock_group_chat):
        """Test successful delegation to a worker."""
        # Setup mocks
        mock_chat_result = Mock()
        mock_chat_result.summary = "Task completed successfully"
        self.mock_self_agent.initiate_chat.return_value = mock_chat_result
        
        # Mock GroupChat with messages - this is what our new implementation reads from
        mock_group_instance = Mock()
        mock_group_instance.messages = [
            {"content": "Initial message"},
            {"content": "Task completed successfully TERMINATE"}
        ]
        mock_manager_instance = Mock()
        mock_group_chat.return_value = mock_group_instance
        mock_group_chat_manager.return_value = mock_manager_instance
        
        # Test delegation
        result = self.delegation_tools.delegate_to_worker("systems_engineer", "Run a test task")
        
        # Verify result
        assert "Delegation to systems_engineer completed" in result
        assert "Task completed successfully TERMINATE" in result
        
        # Verify delegation setup
        self.mock_self_agent.initiate_chat.assert_called_once()
        call_args = self.mock_self_agent.initiate_chat.call_args
        
        # Check that the delegation message includes requestor info
        delegation_message = call_args[1]["message"]
        assert "[DELEGATION FROM senior_architect_1]:" in delegation_message
        assert "Run a test task" in delegation_message
        assert "TERMINATE" in delegation_message
        assert "Note: Respond with 'TERMINATE' to end this delegation when the task is fully complete or when more context is required." in delegation_message
        
        # Check termination message handler
        is_termination_msg = call_args[1]["is_termination_msg"]
        assert is_termination_msg({"content": "TERMINATE"}) == True
        assert is_termination_msg({"content": "continue working"}) == False
    
    def test_delegate_to_worker_not_found(self):
        """Test delegation to non-existent worker."""
        # Make repository return None for worker
        self.mock_role_repository.get_worker.return_value = None
        
        result = self.delegation_tools.delegate_to_worker("non_existent_worker", "Test task")
        
        assert "Worker 'non_existent_worker' not found" in result
        assert "Available workers: ['systems_engineer']" in result
    
    def test_delegate_to_worker_executor_not_found(self):
        """Test delegation when worker executor is not found."""
        # Make worker return None for executor
        self.mock_target_worker.get_executor_agent.return_value = None
        
        result = self.delegation_tools.delegate_to_worker("systems_engineer", "Test task")
        
        assert "Worker executor for worker 'systems_engineer' not found" in result
    
    @patch('autogen.GroupChat')
    @patch('autogen.GroupChatManager')
    def test_delegate_to_worker_exception(self, mock_group_chat_manager, mock_group_chat):
        """Test delegation with exception during chat."""
        # Setup mocks to raise exception
        self.mock_self_agent.initiate_chat.side_effect = Exception("Chat failed")
        
        result = self.delegation_tools.delegate_to_worker("systems_engineer", "Test task")
        
        assert "Error during delegation to systems_engineer" in result
        assert "Chat failed" in result


class TestDelegationToolsIntegration:
    """Integration tests for delegation tools."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_tools_with_valid_params(self):
        """Test get_tools with valid parameters."""
        # Create mock role repository
        mock_role_repository = Mock()
        
        from tools.context import ToolsContext
        tools_context = ToolsContext(
            role_repository=mock_role_repository,
            self_worker_name="test_agent",
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        
        tools = get_tools(tools_context)
        
        # Should return one tool: delegate_to_worker
        assert len(tools) == 1
        assert tools[0].__name__ == "delegate_to_worker"
    
    def test_get_tools_with_missing_params(self):
        """Test get_tools with missing parameters."""
        # Test with None role_repository
        from tools.context import ToolsContext
        tools_context = ToolsContext(
            role_repository=None,
            self_worker_name="test_agent",
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        
        tools = get_tools(tools_context)
        assert len(tools) == 0
        
        # Test with None self_worker_name
        tools_context = ToolsContext(
            role_repository=Mock(),
            self_worker_name=None,
            agent_work_dir=self.temp_dir,
            is_integration_test=True
        )
        tools = get_tools(tools_context) 