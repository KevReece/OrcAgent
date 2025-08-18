#!/usr/bin/env python3

"""
Test module for Associate entity class.
"""

from agents.entities import Associate
from logger.log_wrapper import get_logger

logger = get_logger("test:entities:associate", __name__)


class TestAssociate:
    """Test suite for Associate class."""
    
    def test_associate_creation(self):
        """Test creation of Associate with valid data."""
        associate = Associate(name="test_agent", relationship="Testing relationship")
        
        assert associate.name == "test_agent"
        assert associate.relationship == "Testing relationship"
    
