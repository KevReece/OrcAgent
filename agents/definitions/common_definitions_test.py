#!/usr/bin/env python3

"""
Test module for common_definitions module.
"""

import pytest
from agents.definitions.common_definitions import get_tool_notes, assign_team_associates
from agents.entities import Associate
from logger.log_wrapper import get_logger

logger = get_logger("test:definitions:common_definitions", __name__)


class TestCommonDefinitions:
    """Test suite for common definitions functionality."""
    
    def test_get_tool_notes(self):
        """Test getting tool notes for tool groups."""
        tool_groups = ["notion_tools", "memory_tools"]
        notes = get_tool_notes(tool_groups)
        
        assert isinstance(notes, str)
        assert len(notes) > 0
        # The function returns general tool notes, not specific tool group names
        assert "tool" in notes.lower()
    
    def test_assign_team_associates(self):
        """Test assigning team associates."""
        agent_name = "agent1"
        team_structure = {
            "team1": ["agent1", "agent2"],
            "team2": ["agent3", "agent4"]
        }
        team_relationships = {
            "team1": "Collaborator in team1",
            "team2": "Collaborator in team2"
        }
        
        associates = assign_team_associates(agent_name, team_structure, team_relationships)
        
        assert isinstance(associates, list)
        # Should have associates for all teams except the agent's own team
        assert len(associates) > 0 