#!/usr/bin/env python3
"""
Team Definition Module

This module contains the static definitions for the default team agents
used in the OrcAgent project.
"""

from typing import List, Dict, Any
from agents.entities import Role
from agents.role_repository import RoleRepository
from agents.definitions.common_definitions import get_tool_notes, assign_team_associates

def setup_default_repository(run_dir: str, config_list: List[Dict[str, Any]], 
                            is_integration_test: bool = False) -> RoleRepository:
    """
    Set up the default repository with role definitions and worker instances.
    """
    repository = RoleRepository()
    repository.initialize(run_dir, config_list, is_integration_test)

    # Register role definitions
    role_definitions = get_default_role_definitions()
    for role in role_definitions:
        repository.register_role(role)

    # Create workers
    product_manager_worker = repository.create_worker(role_name="product_manager")
    designer_worker = repository.create_worker(role_name="designer")
    developer_worker = repository.create_worker(role_name="developer")
    tester_worker = repository.create_worker(role_name="tester")
    general_manager_worker = repository.create_worker(role_name="general_manager", is_initiator=True)
    
    # Define the team
    team = {
        "product_team": [
            general_manager_worker.get_name(),
            product_manager_worker.get_name(),
            designer_worker.get_name(),
            developer_worker.get_name(),
            tester_worker.get_name()
        ]
    }
    
    # Set up peer associations for all workers
    all_workers = [
        general_manager_worker,
        product_manager_worker,
        designer_worker,
        developer_worker,
        tester_worker
    ]
    
    for worker in all_workers:
        worker_obj = repository.get_worker(worker.get_name())
        if worker_obj:
            worker_obj.set_associates(assign_team_associates(
                worker.get_name(), 
                team, 
                {"product_team": "Team member"}
            ))
    
    return repository

def get_default_role_definitions() -> List[Role]:
    general_manager_tool_groups = ["notion_tools", "delegation_tools", "memory_tools"]
    general_manager_role = Role(
        role_name="general_manager",
        base_instructions="""You are the general manager. You are responsible for overall project delivery, team orchestration, and ensuring the solution process is opinionated and effective. You must delegate work to the appropriate team members, provide clear direction, and use Notion for documentation and planning. Be decisive and proactive in guiding the team.\n\n""" + get_tool_notes(general_manager_tool_groups),
        description="General manager (initiator, Notion tools, opinionated delegation)",
        role_version=1,
        tool_group_names=general_manager_tool_groups
    )
    
    product_manager_tool_groups = ["notion_tools", "memory_tools"]
    product_manager_role = Role(
        role_name="product_manager",
        base_instructions="""You are the product manager. You own the product strategy and solution. Use Notion for product documentation and planning. Collaborate with the team to ensure the product vision is realized.\n\n""" + get_tool_notes(product_manager_tool_groups),
        description="Product manager (product strategy/solution, Notion tools)",
        role_version=1,
        tool_group_names=product_manager_tool_groups
    )
    
    designer_tool_groups = ["playwright_tools", "web_tools", "notion_tools", "memory_tools"]
    designer_role = Role(
        role_name="designer",
        base_instructions="""You are the designer. You are responsible for user experience and interface design. Use Playwright for prototyping and Notion for design documentation. Collaborate closely with the product manager and developer.\n\n""" + get_tool_notes(designer_tool_groups),
        description="Designer (Playwright and Notion tools)",
        role_version=1,
        tool_group_names=designer_tool_groups
    )
    
    developer_tool_groups = ["file_tools", "git_tools", "github_pr_tools", "github_actions_tools", "notion_tools", "docker_tools", "aws_cli_tools", "playwright_tools", "web_tools", "memory_tools"]
    developer_role = Role(
        role_name="developer",
        base_instructions="""You are the developer. You are responsible for implementing the code and infrastructure. Use code tools, infrastructure tools, Notion, and Playwright as needed. Collaborate with the designer and tester.\n\n""" + get_tool_notes(developer_tool_groups),
        description="Developer (code, infra, Notion, Playwright)",
        role_version=1,
        tool_group_names=developer_tool_groups
    )
    
    tester_tool_groups = ["notion_tools", "playwright_tools", "web_tools", "memory_tools"]
    tester_role = Role(
        role_name="tester",
        base_instructions="""You are the tester. You are responsible for testing and validating the solution. Use Notion for test documentation and Playwright for automated testing. Collaborate with the developer and designer.\n\n""" + get_tool_notes(tester_tool_groups),
        description="Tester (Notion, Playwright)",
        role_version=1,
        tool_group_names=tester_tool_groups
    )
    return [general_manager_role, product_manager_role, designer_role, developer_role, tester_role]
