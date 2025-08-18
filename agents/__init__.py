"""
Agents Module

This module contains agent definitions and configurations.
"""

from .initial_agents import create_and_configure_agents
from .entities import Role, Worker, Associate
from .role_repository import RoleRepository

__all__ = [
    'create_and_configure_agents',
    'Role', 
    'Worker',
    'Associate',
    'RoleRepository',
] 