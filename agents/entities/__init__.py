"""
Entities Package

This package contains the core entity classes for the agent system:
- Role: Defines role types with instructions and capabilities  
- Worker: Represents specific instances of roles with auto-incrementing IDs
- Associate: Defines relationships between workers
"""

from .role import Role
from .worker import Worker, reset_worker_counts, get_worker_count
from .associate import Associate

__all__ = [
    'Role',
    'Worker', 
    'Associate',
    'reset_worker_counts',
    'get_worker_count'
] 