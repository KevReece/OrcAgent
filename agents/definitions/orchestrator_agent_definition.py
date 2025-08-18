#!/usr/bin/env python3
"""
Orchestrator Agent Definition Module

This module contains the static definition for the orchestrator agent used in the OrcAgent project.
"""

from typing import List, Dict, Any
from agents.entities import Role
from agents.role_repository import RoleRepository
from agents.definitions.common_definitions import get_tool_notes

def setup_orchestrator_repository(run_dir: str, config_list: List[Dict[str, Any]], organization_size: str = "dynamic", role_description_complexity: str = "dynamic", is_integration_test: bool = False) -> RoleRepository:
    """
    Set up the repository for the orchestrator agent mode.
    """
    repository = RoleRepository()
    repository.initialize(run_dir, config_list, is_integration_test)

    orchestrator_tool_groups = ["agents_orchestration_tools", "delegation_tools", "memory_tools"]
    all_worker_tool_groups = [
        "aws_cli_tools", "docker_tools", "delegation_tools", "file_tools", "git_tools", "github_actions_tools", "github_pr_tools", "memory_tools", "notion_tools", "playwright_tools", "web_tools"
    ]
    organization_size_instructions_lookup = {
        "dynamic": "The organization size should be dynamically determined based on the complexity of the prompt and the complexity of the task. ",
        "small": "It is important that the organization be small sized, consisting of around 5 workers. ",
        "medium": "It is important that the organization be medium sized, consisting of around 25 workers. ",
        "large": "It is important that the organization be large sized, consisting of around 50 workers. "
    }
    role_description_complexity_instructions_lookup = {
        "dynamic": "The role description complexity should be dynamically determined based on the specific needs of the task. ",
        "minimal": "It is important that the roles each have minimal descriptions, limited to concise core responsibilities. ",
        "balanced": "It is important that the roles each have balanced descriptions, giving the breadth of responsibilities without being prescriptive, and some specific relevant extra context. ",
        "extensive": "It is important that the roles each have extensive descriptions, covering the full extent of responsibilities in meticulous detail, and with the addition of broad supporting information into even loosely related context. "
    }
    orchestrator_role = Role(
        role_name="orchestrator",
        base_instructions=(
            "You are the orchestrator. You do not perform implementation work directly. "
            "Your job is to orchestrate a product development organization (roles and workers) using the agent orchestration tools, to be best able to independently deliver on the prompted mandate, and then delegate a team member to carry out the prompt independently. "
            "You must design the organization, assign roles, and provide highly detailed, clear and comprehensive instructions to each worker. "
            + organization_size_instructions_lookup[organization_size]
            + role_description_complexity_instructions_lookup[role_description_complexity]
            + "Your instructions and prompt must target achieving a maximal level of professionalism covering all phases of the product development lifecycle and with polished deliverables, in order to form a world class product delivery organization."
            "You need to create roles with instructions for enterprise-level professionals. "
            "Your role prompt engineering must create fully fleshed out workers with all of the wider expectations of the role, as in a real world business. "
            "When defining roles there should be explicit expectations of time management and high quality deliverables, including explicit responsibilities for functional and non-functional delivery goals. "
            "You must ensure the workers have comprehensive clarity on their responsibilities and associates responsibilities, such that they always delegate and collaborate appropriately. "
            "You must ensure each role knows what tools they should use to carry out their responsibilities. "
            "You must create a single leader worker as your delegate. This lead can be CEO or down to a team lead, but must be the fully accountable individual for the task. "
            "When you delegate to the leader worker you must give them the entire context required to be able to fully complete every aspect of the task. "
            "Ensure the leader worker is tasked to ensure the creation of a comprehensive and specific plan with comprehensively defined ownership, including expectations of immediate deliverables. "
            "When receiving a response from the leader worker, if any aspect of the task is not complete and comprehensively validated as complete, with iron clad evidence, you must re-delegate back to the leader worker to rectify the task and task validation, again with all the sufficient context to fully complete the task."
            "Only ever delegate to the leader worker, never to the workers directly. "
            "To be clear, implementation must be complete with evidence, such as a testing completion report of all functional and non-functional requirements passing, anything less must be rejected. "
            "You always need at least 2 developers for PR review purposes."
            "The available tools groups are: " + ', '.join(all_worker_tool_groups) + "."
            "You can't use implementation tools directly, but you should reference them extensively in your planning and instructions.\n\n"
            + get_tool_notes(orchestrator_tool_groups)
        ),
        description="Orchestrator with only agent orchestration tools and memory. Mandated to create and instruct an organization to deliver on the prompt.",
        role_version=1,
        tool_group_names=orchestrator_tool_groups
    )
    repository.register_role(orchestrator_role)
    repository.create_worker(
        role_name="orchestrator",
        is_initiator=True
    )
    return repository 