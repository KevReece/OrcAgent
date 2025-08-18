#!/usr/bin/env python3
"""
Company Definition Module

This module contains the static definition for a full company structure with multiple teams and roles.
"""

from typing import List, Dict, Any
from agents.entities import Role, Associate
from agents.role_repository import RoleRepository
from agents.definitions.common_definitions import get_tool_notes, assign_team_associates

def get_company_role_definitions() -> List[Role]:
    """Get the role definitions for the company structure."""
    
    # Executive roles
    ceo_tool_groups = ["notion_tools", "delegation_tools", "memory_tools"]
    ceo = Role("ceo", "You are the CEO. You lead the company and set the vision. Delegate to the executive team.\n\n" + get_tool_notes(ceo_tool_groups), "CEO (initiator)", 1, ceo_tool_groups)
    
    cfo_tool_groups = ["notion_tools", "memory_tools"]
    cfo = Role("cfo", "You are the CFO. You are responsible for financial operations and budgeting.\n\n" + get_tool_notes(cfo_tool_groups), "CFO", 1, cfo_tool_groups)
    
    cmo_tool_groups = ["notion_tools", "memory_tools"]
    cmo = Role("cmo", "You are the CMO. You are responsible for marketing and growth strategies.\n\n" + get_tool_notes(cmo_tool_groups), "CMO", 1, cmo_tool_groups)
    
    ctpo_tool_groups = ["notion_tools", "delegation_tools", "memory_tools"]
    ctpo = Role("ctpo", "You are the CTPO (Chief Technology & Product Officer). You lead all engineering and product teams.\n\n" + get_tool_notes(ctpo_tool_groups), "CTPO", 1, ctpo_tool_groups)
    
    # Generic product team roles (used by all teams)
    eng_manager_tool_groups = ["notion_tools", "delegation_tools", "memory_tools"]
    engineering_manager = Role("engineering_manager", "You are an Engineering Manager. You lead the technical implementation for your product team.\n\n" + get_tool_notes(eng_manager_tool_groups), "Engineering Manager", 1, eng_manager_tool_groups)
    
    product_manager_tool_groups = ["notion_tools", "memory_tools", "delegation_tools", "playwright_tools", "web_tools"]
    product_manager = Role("product_manager", "You are a Product Manager. You own the product strategy and roadmap for your product team.\n\n" + get_tool_notes(product_manager_tool_groups), "Product Manager", 1, product_manager_tool_groups)
    
    designer_tool_groups = ["notion_tools", "playwright_tools", "web_tools", "memory_tools", "delegation_tools"]
    designer = Role("designer", "You are a Designer. You design user experience and interfaces for your product team.\n\n" + get_tool_notes(designer_tool_groups), "Designer", 1, designer_tool_groups)
    
    developer_tool_groups = ["file_tools", "git_tools", "notion_tools", "aws_cli_tools", "docker_tools", "github_pr_tools", "github_actions_tools", "playwright_tools", "web_tools", "memory_tools", "delegation_tools"]
    developer = Role("developer", "You are a Developer. You implement code and infrastructure for your product team.\n\n" + get_tool_notes(developer_tool_groups), "Developer", 1, developer_tool_groups)
    
    tester_tool_groups = ["notion_tools", "playwright_tools", "web_tools", "memory_tools", "delegation_tools"]
    tester = Role("tester", "You are a Tester. You test and validate solutions for your product team.\n\n" + get_tool_notes(tester_tool_groups), "Tester", 1, tester_tool_groups)
    
    return [ceo, cfo, cmo, ctpo, engineering_manager, product_manager, designer, developer, tester]



def setup_company_repository(run_dir: str, config_list: List[Dict[str, Any]], is_integration_test: bool = False) -> RoleRepository:
    """
    Set up the repository for the company mode with 3 product teams.
    """
    repository = RoleRepository()
    repository.initialize(run_dir, config_list, is_integration_test)
    
    role_definitions = get_company_role_definitions()
    for role in role_definitions:
        repository.register_role(role)
    
    # Create workers for executive team
    executive_team_memory = [("I am a member of Executive Team. I work closely with my Executive Team teammates to deliver our team's objectives.", 1)]
    cfo_worker = repository.create_worker_with_memories("cfo", executive_team_memory)
    cmo_worker = repository.create_worker_with_memories("cmo", executive_team_memory)
    ctpo_worker = repository.create_worker_with_memories("ctpo", executive_team_memory)
    ceo_worker = repository.create_worker_with_memories("ceo", executive_team_memory, is_initiator=True)
    
    # Create workers for Product Team A
    team_a_memory = [("I am a member of Product Team A. I work closely with my Product Team A teammates to deliver our team's objectives.", 1)]
    eng_manager_a_worker = repository.create_worker_with_memories("engineering_manager", team_a_memory)
    product_manager_a_worker = repository.create_worker_with_memories("product_manager", team_a_memory)
    designer_a_worker = repository.create_worker_with_memories("designer", team_a_memory)
    developer_a_worker = repository.create_worker_with_memories("developer", team_a_memory)
    tester_a_worker = repository.create_worker_with_memories("tester", team_a_memory)
    
    # Create workers for Product Team B
    team_b_memory = [("I am a member of Product Team B. I work closely with my Product Team B teammates to deliver our team's objectives.", 1)]
    eng_manager_b_worker = repository.create_worker_with_memories("engineering_manager", team_b_memory)
    product_manager_b_worker = repository.create_worker_with_memories("product_manager", team_b_memory)
    designer_b_worker = repository.create_worker_with_memories("designer", team_b_memory)
    developer_b_worker = repository.create_worker_with_memories("developer", team_b_memory)
    tester_b_worker = repository.create_worker_with_memories("tester", team_b_memory)
    
    # Create workers for Product Team C
    team_c_memory = [("I am a member of Product Team C. I work closely with my Product Team C teammates to deliver our team's objectives.", 1)]
    eng_manager_c_worker = repository.create_worker_with_memories("engineering_manager", team_c_memory)
    product_manager_c_worker = repository.create_worker_with_memories("product_manager", team_c_memory)
    designer_c_worker = repository.create_worker_with_memories("designer", team_c_memory)
    developer_c_worker = repository.create_worker_with_memories("developer", team_c_memory)
    tester_c_worker = repository.create_worker_with_memories("tester", team_c_memory)
    
    # Define the 5 teams with peer associations
    teams = {
        "c_level": [
            ceo_worker.get_name(),
            cfo_worker.get_name(),
            cmo_worker.get_name(),
            ctpo_worker.get_name()
        ],
        "engineering_management": [
            ctpo_worker.get_name(),
            eng_manager_a_worker.get_name(),
            eng_manager_b_worker.get_name(),
            eng_manager_c_worker.get_name()
        ],
        "team_a": [
            eng_manager_a_worker.get_name(),
            product_manager_a_worker.get_name(),
            designer_a_worker.get_name(),
            developer_a_worker.get_name(),
            tester_a_worker.get_name()
        ],
        "team_b": [
            eng_manager_b_worker.get_name(),
            product_manager_b_worker.get_name(),
            designer_b_worker.get_name(),
            developer_b_worker.get_name(),
            tester_b_worker.get_name()
        ],
        "team_c": [
            eng_manager_c_worker.get_name(),
            product_manager_c_worker.get_name(),
            designer_c_worker.get_name(),
            developer_c_worker.get_name(),
            tester_c_worker.get_name()
        ]
    }
    
    # Define relationship descriptions for each team
    relationship_descriptions = {
        "c_level": "C-level executive",
        "engineering_management": "Engineering management",
        "team_a": "Product Team A",
        "team_b": "Product Team B",
        "team_c": "Product Team C"
    }
    
    # Set up peer associations for all workers
    all_workers = [
        ceo_worker, cfo_worker, cmo_worker, ctpo_worker,
        eng_manager_a_worker, eng_manager_b_worker, eng_manager_c_worker,
        product_manager_a_worker, product_manager_b_worker, product_manager_c_worker,
        designer_a_worker, designer_b_worker, designer_c_worker,
        developer_a_worker, developer_b_worker, developer_c_worker,
        tester_a_worker, tester_b_worker, tester_c_worker
    ]
    
    for worker in all_workers:
        worker_obj = repository.get_worker(worker.get_name())
        if worker_obj:
            worker_obj.set_associates(assign_team_associates(
                worker.get_name(),
                teams,
                relationship_descriptions
            ))
    
    return repository 