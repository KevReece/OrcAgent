#!/usr/bin/env python3

"""
Test module for team_definition module.
"""

import pytest
import tempfile
from agents.definitions.team_definition import setup_default_repository
from logger.log_wrapper import get_logger

logger = get_logger("test:definitions:team_definition", __name__)


class TestTeamDefinition:
    """Test suite for team definition functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_default_repository(self):
        """Test setting up default repository."""
        repository = setup_default_repository(self.temp_dir, self.config_list, is_integration_test=True)
        
        assert repository is not None
        assert repository.get_role("general_manager") is not None
        
        # Check that general manager worker was created as initiator
        gm_worker = repository.get_worker("general_manager_1")
        assert gm_worker is not None
        assert gm_worker.is_initiator == True 