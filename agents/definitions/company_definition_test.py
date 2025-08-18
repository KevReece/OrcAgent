#!/usr/bin/env python3

"""
Test module for company_definition module.
"""

import pytest
import tempfile
from agents.definitions.company_definition import setup_company_repository
from logger.log_wrapper import get_logger

logger = get_logger("test:definitions:company_definition", __name__)


class TestCompanyDefinition:
    """Test suite for company definition functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_list = [{"model": "gpt-4.1-nano", "api_key": "test_key"}]
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_company_repository(self):
        """Test setting up company repository."""
        repository = setup_company_repository(self.temp_dir, self.config_list, is_integration_test=True)
        
        assert repository is not None
        assert repository.get_role("ceo") is not None
        assert repository.get_role("ctpo") is not None
        assert repository.get_role("cfo") is not None
        assert repository.get_role("cmo") is not None
        
        # Check that CEO worker was created as initiator
        ceo_worker = repository.get_worker("ceo_1")
        assert ceo_worker is not None
        assert ceo_worker.is_initiator == True 