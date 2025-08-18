"""
Role Entity Class

This module defines the Role class which represents role type definitions for agent creation.
"""

from typing import List, Optional
from dataclasses import dataclass, field
from logger.log_wrapper import get_logger

logger = get_logger("agents:entities:role", __name__)


@dataclass
class Role:
    """
    Represents a role type definition for agent creation.
    
    This class defines the type of role (e.g., "architect", "systems_engineer")
    without worker-specific information like worker_id or associates.
    
    Attributes:
        role_name: Unique identifier for the role type
        base_instructions: Core instructions that define the role's behavior
        description: Description of what this role does
        role_version: Version number for the role definition
        tool_group_names: List of tool groups this role type has access to
    """
    role_name: str
    base_instructions: str
    description: str
    role_version: int = 1
    tool_group_names: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate role configuration after initialization."""
        from agents.definitions.common_definitions import get_universal_instructions
        self.base_instructions = self.base_instructions + get_universal_instructions()
        self._validate_role()
        logger.debug(f"Created role: {self.role_name}")
    
    def _validate_role(self) -> None:
        """Validate required role fields and constraints."""
        if not self.role_name or not self.role_name.strip():
            raise ValueError("role_name cannot be empty")
        
        if not self.base_instructions or not self.base_instructions.strip():
            raise ValueError("base_instructions cannot be empty")
        
        if not self.description or not self.description.strip():
            raise ValueError("description cannot be empty")
        
        if self.role_version < 1:
            raise ValueError("role_version must be >= 1")
        
        # Validate tool group names
        invalid_tool_groups = [name for name in self.tool_group_names if not name or not name.strip()]
        if invalid_tool_groups:
            raise ValueError("All tool group names must be non-empty strings")
    
    def add_tool_group(self, tool_group_name: str) -> None:
        """
        Add a tool group to this role type's accessible tools.
        
        Args:
            tool_group_name: Name of the tool group to add
        """
        if not tool_group_name or not tool_group_name.strip():
            raise ValueError("Tool group name cannot be empty")
        
        if tool_group_name not in self.tool_group_names:
            self.tool_group_names.append(tool_group_name)
            logger.debug(f"Added tool group '{tool_group_name}' to role '{self.role_name}'")
        else:
            logger.debug(f"Tool group '{tool_group_name}' already exists in role '{self.role_name}'")
    
    def clone(self, new_role_name: Optional[str] = None) -> 'Role':
        """
        Create a clone of this role type with optional modifications.
        
        Args:
            new_role_name: Optional new role name for the clone
            
        Returns:
            Role: Cloned role instance
        """
        clone = Role(
            role_name=new_role_name or self.role_name,
            base_instructions=self.base_instructions,
            description=self.description,
            role_version=self.role_version,
            tool_group_names=self.tool_group_names.copy()
        )
        
        logger.debug(f"Cloned role '{self.role_name}' to '{clone.role_name}'")
        return clone
    
    def __str__(self) -> str:
        """String representation of the role."""
        return f"Role({self.role_name}, v{self.role_version})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the role."""
        return (f"Role(role_name='{self.role_name}', role_version={self.role_version}, "
                f"tool_groups={len(self.tool_group_names)})") 