#!/usr/bin/env python3

"""
Test module for orchestrator_agent_definition module.
"""

import pytest
import tempfile
from agents.definitions.orchestrator_agent_definition import setup_orchestrator_repository
from logger.log_wrapper import get_logger

logger = get_logger("test:definitions:orchestrator_agent_definition", __name__)


class TestOrchestratorAgentDefinition:
    """Test suite for orchestrator agent definition functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_orchestrator_repository(self):
        """Test setting up orchestrator repository."""
        repository = setup_orchestrator_repository(self.temp_dir, self.config_list, is_integration_test=True)
        
        assert repository is not None
        assert repository.get_role("orchestrator") is not None
        
        # Check that orchestrator worker was created as initiator
        orchestrator_worker = repository.get_worker("orchestrator_1")
        assert orchestrator_worker is not None
        assert orchestrator_worker.is_initiator == True 