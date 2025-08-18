#!/usr/bin/env python3
"""
Agents Orchestration Tools Module

This module provides tools for orchestrating agents, including creating workers,
defining roles with versioning, and managing worker associations.
"""

import re
from typing import Optional
from logger.log_wrapper import get_logger

logger = get_logger("tools:agents_orchestration", __name__)


def get_tools(tools_context):
    """
    Get agents orchestration tools for an agent.
    Args:
        tools_context: ToolsContext instance
    Returns:
        List of tool functions
    """
    if not tools_context.role_repository:
        logger.warning("Agents orchestration tools require role_repository - returning empty list")
        return []
    logger.info("Creating agents orchestration tools")

    """
    Creates a worker from a role
    Args:
        role_name: Role name
        associates: optional json string containing an array of (worker name, relationship) to associate to the new worker
    Returns:
        string summarising the tool outcome
    """
    def create_worker(role_name: str, associates: Optional[str] = None) -> str:
        parsed_associates = None
        if associates:
            try:
                import json
                parsed_associates = json.loads(associates)
            except Exception as e:
                return f"Error parsing associates JSON: {str(e)}"
        try:
            role = tools_context.role_repository.get_role(role_name)
            if not role:
                return f"Error: Role '{role_name}' not found in repository"
            worker = tools_context.role_repository.create_worker(
                role_name=role_name,
                associates=parsed_associates,
                is_initiator=False
            )
            if parsed_associates:
                for associate_name, _ in parsed_associates:
                    associate_worker = tools_context.role_repository.get_worker(associate_name)
                    if associate_worker:
                        associate_worker._associated_from.append(worker.get_name())
                        logger.info(f"Added '{worker.get_name()}' to '{associate_name}' associated_from list")
                    else:
                        logger.warning(f"Associate worker '{associate_name}' not found")
            else:
                logger.info("No associates provided for worker creation")
            return f"Successfully created worker '{worker.get_name()}' with role '{role_name}' (version {role.role_version})"
        except Exception as e:
            return f"Error creating worker for role '{role_name}': {str(e)}"
        
    """
    Creates a role
    Args:
        role_name: Role name 
            (only alphabetic characters allowed, non-alphabetic characters are removed)
            (using an existing role name will overwrite the existing role as new version)
        base_instructions: base instructions for the worker agent
        description: string description of the role
        tool_group_names: list of the tool groups to enable for the role workers
            (superset of tool group names: ["aws_cli_tools", "docker_tools", "delegation_tools", "file_tools", "git_tools", "github_actions_tools", "github_pr_tools", "memory_tools", "notion_tools", "playwright_tools", "web_tools"])
    Returns:
        string summarising the tool outcome
    """
    def define_role(role_name: str, base_instructions: str, description: str, tool_group_names: list[str]) -> str:
        # Sanitize role name (only alphabetic characters allowed)
        role_name = re.sub(r'[^a-zA-Z]', '', role_name)
        if not role_name:
            return f"Error: Role name '{role_name}' is invalid"
        
        parsed_tool_groups: list[str] = []
        # Validate provided tool groups are a non-empty list of strings
        if not isinstance(tool_group_names, list) or not tool_group_names or not all(isinstance(item, str) for item in tool_group_names):
            return "Error: tool_group_names must be a non-empty list of strings"
        parsed_tool_groups = list(tool_group_names)
        if "delegation_tools" not in parsed_tool_groups:
            parsed_tool_groups.append("delegation_tools")
        if "memory_tools" not in parsed_tool_groups:
            parsed_tool_groups.append("memory_tools")
        try:
            current_role = tools_context.role_repository.get_role(role_name)
            new_version = 1
            if current_role:
                new_version = current_role.role_version + 1
            from agents.entities import Role
            new_role = Role(
                role_name=role_name,
                base_instructions=base_instructions,
                description=description,
                role_version=new_version,
                tool_group_names=parsed_tool_groups or []
            )
            tools_context.role_repository.register_role(new_role)
            return f"Successfully defined role '{role_name}' version {new_version}"
        except Exception as e:
            return f"Error defining role '{role_name}': {str(e)}"
        
    """
    Get a role (latest version)
    Args:
        role_name: Role name
    Returns:
        string details the role
    """
    def get_role(role_name: str) -> str:
        try:
            role = tools_context.role_repository.get_role(role_name)
            if not role:
                return f"Error: Role '{role_name}' not found in repository"
            return (f"Role '{role_name}' (version {role.role_version}):\n"
                    f"Description: {role.description}\n"
                    f"Tool Groups: {', '.join(role.tool_group_names) if role.tool_group_names else 'None'}\n"
                    f"Base Instructions: {role.base_instructions}")
        except Exception as e:
            return f"Error getting role '{role_name}': {str(e)}"
        
    """
    Get a specific role version
    Args:
        role_name: Role name
        version: integer of the incrementing role version
    Returns:
        string details of the role
    """
    def get_role_version(role_name: str, version: int) -> str:
        try:
            role = tools_context.role_repository.get_role(role_name)
            if not role:
                return f"Error: Role '{role_name}' not found in repository"
            if role.role_version != version:
                return f"Error: Role '{role_name}' version {version} not found. Current version is {role.role_version}"
            return (f"Role '{role_name}' (version {role.role_version}):\n"
                    f"Description: {role.description}\n"
                    f"Tool Groups: {', '.join(role.tool_group_names) if role.tool_group_names else 'None'}\n"
                    f"Base Instructions: {role.base_instructions}")
        except Exception as e:
            return f"Error getting role '{role_name}' version {version}: {str(e)}"
    
    """
    Get a worker
    Args:
        worker_name: Worker name
    Returns:
        string details of the worker
    """
    def get_worker(worker_name: str) -> str:
        try:
            worker = tools_context.role_repository.get_worker(worker_name)
            if not worker:
                return f"Error: Worker '{worker_name}' not found in repository"
            associated_from = worker._associated_from
            return (f"Worker '{worker_name}':\n"
                    f"Role: {worker.role.role_name} (version {worker.role.role_version})\n"
                    f"Worker ID: {worker.worker_id}\n"
                    f"Is Initiator: {worker.is_initiator}\n"
                    f"Associates: {len(worker._associates)}\n"
                    f"Associated From: {len(associated_from)} workers\n"
                    f"Memories: {worker.memory.get_memory_count()}")
        except Exception as e:
            return f"Error getting worker '{worker_name}': {str(e)}"
        
    """
    Delete a worker
    Args:
        worker_name: Worker name
    Returns:
        string summarising the tool outcome
    """
    def delete_worker(worker_name: str) -> str:
        try:
            deleted = tools_context.role_repository.delete_worker(worker_name)
            if deleted:
                return f"Successfully deleted worker '{worker_name}'"
            else:
                return f"Error: Worker '{worker_name}' not found in repository"
        except Exception as e:
            return f"Error deleting worker '{worker_name}': {str(e)}"
        
    """
    Add a worker associate
    Args:
        worker_name: Worker name
        associate_worker_name: Associate worker name
    Returns:
        string summarising the tool outcome
    """
    def add_worker_associate(worker_name: str, associate_worker_name: str) -> str:
        try:
            worker = tools_context.role_repository.get_worker(worker_name)
            if not worker:
                return f"Error: Worker '{worker_name}' not found in repository"
            associate_worker = tools_context.role_repository.get_worker(associate_worker_name)
            if not associate_worker:
                return f"Error: Associated worker '{associate_worker_name}' not found in repository"
            worker.set_associate(associate_worker)
            return f"Successfully added '{associate_worker_name}' as '{worker_name}' associate"
        except Exception as e:
            return f"Error adding '{associate_worker_name}' as '{worker_name}' associate': {str(e)}"
    
    return [
        create_worker,
        define_role,
        get_role,
        get_role_version,
        get_worker,
        delete_worker,
        add_worker_associate,
    ] 
        