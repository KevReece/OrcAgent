#!/usr/bin/env python3

"""
Test module for solo_agent_definition module.
"""

import pytest
import tempfile
from agents.definitions.solo_agent_definition import setup_solo_repository
from logger.log_wrapper import get_logger

logger = get_logger("test:definitions:solo_agent_definition", __name__)


class TestSoloAgentDefinition:
    """Test suite for solo agent definition functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_solo_repository(self):
        """Test setting up solo repository."""
        repository = setup_solo_repository(self.temp_dir, self.config_list, is_integration_test=True)
        
        assert repository is not None
        assert repository.get_role("solo_founder") is not None
        
        # Check that solo founder worker was created as initiator
        solo_worker = repository.get_worker("solo_founder_1")
        assert solo_worker is not None
        assert solo_worker.is_initiator == True 