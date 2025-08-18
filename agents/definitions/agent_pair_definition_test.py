#!/usr/bin/env python3

"""
Test module for agent_pair_definition module.
"""

import tempfile
from agents.definitions.agent_pair_definition import setup_agent_pair_repository
from logger.log_wrapper import get_logger

logger = get_logger("test:definitions:agent_pair_definition", __name__)


class TestAgentPairDefinition:
    """Test suite for agent pair definition functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_agent_pair_repository(self):
        """Test setting up agent pair repository."""
        repository = setup_agent_pair_repository(self.temp_dir, self.config_list, is_integration_test=True)
        
        assert repository is not None
        assert repository.get_role("founder_ceo") is not None
        assert repository.get_role("founder_cto") is not None
        
        # Check that workers were created
        founder_ceo_worker = repository.get_worker("founder_ceo_1")
        founder_cto_worker = repository.get_worker("founder_cto_1")
        
        assert founder_ceo_worker is not None
        assert founder_cto_worker is not None
        assert founder_ceo_worker.is_initiator == True
        assert founder_cto_worker.is_initiator == False 