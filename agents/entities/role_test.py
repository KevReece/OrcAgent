#!/usr/bin/env python3

"""
Test module for Role entity class.
"""

import pytest
from agents.entities import Role
from logger.log_wrapper import get_logger

logger = get_logger("test:entities:role", __name__)


class TestRole:
    """Test suite for Role class."""
    
    def test_role_creation_minimal(self):
        """Test creation of Role with minimal required fields."""
        role = Role(
            role_name="test_role",
            base_instructions="Test instructions",
            description="Test description"
        )
        
        assert role.role_name == "test_role"
        assert role.base_instructions == "Test instructions"
        assert role.description == "Test description"
        assert role.role_version == 1
        assert role.tool_group_names == []
    
    def test_role_creation_full(self):
        """Test creation of Role with all fields specified."""
        role = Role(
            role_name="full_role",
            base_instructions="Full instructions",
            description="Full description",
            role_version=2,
            tool_group_names=["tools1", "tools2"]
        )
        
        assert role.role_name == "full_role"
        assert role.base_instructions == "Full instructions"
        assert role.description == "Full description"
        assert role.role_version == 2
        assert role.tool_group_names == ["tools1", "tools2"]
    
    def test_role_validation_empty_role_name(self):
        """Test that empty role_name raises ValueError."""
        with pytest.raises(ValueError, match="role_name cannot be empty"):
            Role(role_name="", base_instructions="Test instructions", description="Test desc")
        
        with pytest.raises(ValueError, match="role_name cannot be empty"):
            Role(role_name="   ", base_instructions="Test instructions", description="Test desc")
    
    def test_role_validation_empty_base_instructions(self):
        """Test that empty base_instructions raises ValueError."""
        with pytest.raises(ValueError, match="base_instructions cannot be empty"):
            Role(role_name="test_role", base_instructions="", description="Test desc")
        
        with pytest.raises(ValueError, match="base_instructions cannot be empty"):
            Role(role_name="test_role", base_instructions="   ", description="Test desc")
    
    def test_role_validation_empty_description(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            Role(role_name="test_role", base_instructions="Test instructions", description="")
        
        with pytest.raises(ValueError, match="description cannot be empty"):
            Role(role_name="test_role", base_instructions="Test instructions", description="   ")
    
    def test_role_validation_invalid_role_version(self):
        """Test that invalid role_version raises ValueError."""
        with pytest.raises(ValueError, match="role_version must be >= 1"):
            Role(role_name="test_role", base_instructions="Test", description="Test desc", role_version=0)
        
        with pytest.raises(ValueError, match="role_version must be >= 1"):
            Role(role_name="test_role", base_instructions="Test", description="Test desc", role_version=-1)
    
    def test_role_validation_invalid_tool_groups(self):
        """Test that invalid tool group names raise ValueError."""
        with pytest.raises(ValueError, match="All tool group names must be non-empty strings"):
            Role(
                role_name="test_role",
                base_instructions="Test",
                description="Test desc",
                tool_group_names=["valid", "", "also_valid"]
            )
    
    def test_add_tool_group(self):
        """Test adding tool groups to a role."""
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        
        role.add_tool_group("tools1")
        role.add_tool_group("tools2")
        
        assert role.tool_group_names == ["tools1", "tools2"]
        
        # Test adding duplicate - should not duplicate
        role.add_tool_group("tools1")
        assert role.tool_group_names == ["tools1", "tools2"]
    
    def test_add_tool_group_validation(self):
        """Test validation when adding tool groups."""
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc")
        
        with pytest.raises(ValueError, match="Tool group name cannot be empty"):
            role.add_tool_group("")
        
        with pytest.raises(ValueError, match="Tool group name cannot be empty"):
            role.add_tool_group("   ")
    
    def test_role_clone_default(self):
        """Test cloning a role with default parameters."""
        original = Role(
            role_name="original_role",
            base_instructions="Original instructions",
            description="Original description",
            role_version=2,
            tool_group_names=["tools1"]
        )
        
        clone = original.clone()
        
        # Should be identical but separate instances
        assert clone.role_name == original.role_name
        assert clone.base_instructions == original.base_instructions
        assert clone.description == original.description
        assert clone.role_version == original.role_version
        assert clone.tool_group_names == original.tool_group_names
        assert clone.tool_group_names is not original.tool_group_names  # Different list objects
    
    def test_role_clone_with_new_name(self):
        """Test cloning a role with a new name."""
        original = Role(role_name="original_role", base_instructions="Original instructions", description="Original desc")
        
        clone = original.clone(new_role_name="cloned_role")
        
        assert clone.role_name == "cloned_role"
        assert clone.base_instructions == original.base_instructions
        assert clone.description == original.description
        assert original.role_name == "original_role"  # Original unchanged
    
    def test_str_representation(self):
        """Test string representation of Role."""
        role = Role(role_name="test_role", base_instructions="Test", description="Test desc", role_version=2)
        
        result = str(role)
        expected = "Role(test_role, v2)"
        
        assert result == expected
    
    def test_repr_representation(self):
        """Test detailed string representation of Role."""
        role = Role(
            role_name="test_role",
            base_instructions="Test",
            description="Test desc",
            role_version=2,
            tool_group_names=["tools1", "tools2"]
        )
        
        result = repr(role)
        expected = "Role(role_name='test_role', role_version=2, tool_groups=2)"
        
        assert result == expected 