#!/usr/bin/env python3
"""
Solo Agent Definition Module

This module contains the static definition for the solo agent.
"""

from typing import List, Dict, Any
from agents.entities import Role
from agents.role_repository import RoleRepository
from agents.definitions.common_definitions import get_tool_notes

def setup_solo_repository(run_dir: str, config_list: List[Dict[str, Any]], is_integration_test: bool = False) -> RoleRepository:
    """
    Set up the repository for the solo agent mode.
    """
    repository = RoleRepository()
    repository.initialize(run_dir, config_list, is_integration_test)

    # Register solo role definition
    tool_group_names = [
        "aws_cli_tools", "docker_tools", "file_tools", "git_tools", "github_actions_tools", "github_pr_tools", "memory_tools", "notion_tools", "playwright_tools", "web_tools"
    ]
    solo_role = Role(
        role_name="solo_founder",
        base_instructions=(
            "You are a Solo Founder. You are responsible for all aspects of building and launching a software business, including vision, planning, coding, design, testing, deployment, documentation, and go-to-market. "
            "You must use all available tools and resources to deliver the project end-to-end as a professional solo founder.\n\n"
            + get_tool_notes(tool_group_names)
        ),
        description="Solo founder with full responsibility and access to all tools.",
        role_version=1,
        tool_group_names=tool_group_names
    )
    repository.register_role(solo_role)

    # Create the solo worker (initiator, no associates)
    repository.create_worker(
        role_name="solo_founder",
        is_initiator=True
    )

    return repository 