"""
Definitions Package

This package contains the agent definition modules for different team structures:
- agent_pair_definition: Founder CEO and Founder CTO pair
- company_definition: Company structure with CEO, CTO, CFO, COO
- team_definition: Default team structure
- orchestrator_agent_definition: Orchestrator agent
- solo_agent_definition: Solo Founder
- common_definitions: Shared utilities and functions
"""

from .agent_pair_definition import setup_agent_pair_repository
from .company_definition import setup_company_repository
from .team_definition import setup_default_repository
from .orchestrator_agent_definition import setup_orchestrator_repository
from .solo_agent_definition import setup_solo_repository
from .common_definitions import get_tool_notes, assign_team_associates

__all__ = [
    'setup_agent_pair_repository',
    'setup_company_repository',
    'setup_default_repository',
    'setup_orchestrator_repository',
    'setup_solo_repository',
    'get_tool_notes',
    'assign_team_associates'
] 