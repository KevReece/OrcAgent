#!/usr/bin/env python3
"""
Agent Pair Definition Module

This module contains the static definition for the agent pair (planner and implementer).
"""

from typing import List, Dict, Any
from agents.entities import Role
from agents.role_repository import RoleRepository
from agents.definitions.common_definitions import get_tool_notes, assign_team_associates

def setup_agent_pair_repository(run_dir: str, config_list: List[Dict[str, Any]], is_integration_test: bool = False) -> RoleRepository:
    """
    Set up the repository for the agent pair mode.
    """
    repository = RoleRepository()
    repository.initialize(run_dir, config_list, is_integration_test)

    # Define roles
    founder_ceo_tool_groups = ["notion_tools", "memory_tools", "delegation_tools"]
    founder_cto_tool_groups = ["aws_cli_tools", "docker_tools", "github_pr_tools", "github_actions_tools", "memory_tools", "notion_tools"]
    
    founder_ceo_role = Role(
        role_name="founder_ceo",
        base_instructions=(
            "You are the Founder CEO. You are responsible for high-level vision, business strategy, planning, and early documentation. "
            "You must delegate all technical implementation tasks to the Founder CTO and ensure the project aligns with business goals.\n\n"
            + get_tool_notes(founder_ceo_tool_groups)
        ),
        description="Founder CEO with responsibility for vision, business strategy, planning, and orchestration tools.",
        role_version=1,
        tool_group_names=founder_ceo_tool_groups
    )
    founder_cto_role = Role(
        role_name="founder_cto",
        base_instructions=(
            "You are the Founder CTO. You are responsible for technical execution, architecture, coding, testing, and deployment. "
            "You must follow the Founder CEO's direction, report progress, and ensure technical excellence.\n\n"
            + get_tool_notes(founder_cto_tool_groups)
        ),
        description="Founder CTO with responsibility for technical execution and all engineering tools.",
        role_version=1,
        tool_group_names=founder_cto_tool_groups
    )
    repository.register_role(founder_ceo_role)
    repository.register_role(founder_cto_role)

    # Create workers
    founder_cto_worker = repository.create_worker(role_name="founder_cto")
    founder_ceo_worker = repository.create_worker(role_name="founder_ceo", is_initiator=True)
    
    # Define the pair team
    pair_team = {
        "agent_pair": [founder_ceo_worker.get_name(), founder_cto_worker.get_name()]
    }
    
    # Set up peer associations for both workers
    founder_ceo_associates = assign_team_associates(founder_ceo_worker.get_name(), pair_team, {"agent_pair": "Peer collaborator in agent pair"})
    founder_cto_associates = assign_team_associates(founder_cto_worker.get_name(), pair_team, {"agent_pair": "Peer collaborator in agent pair"})
    
    # Update worker associates
    ceo_obj = repository.get_worker(founder_ceo_worker.get_name())
    if ceo_obj:
        ceo_obj.set_associates(founder_ceo_associates)
    
    cto_obj = repository.get_worker(founder_cto_worker.get_name())
    if cto_obj:
        cto_obj.set_associates(founder_cto_associates)
    
    return repository 