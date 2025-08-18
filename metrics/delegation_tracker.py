#!/usr/bin/env python3
"""
Delegation Tracker Module

Tracks delegation trees and outputs them in a file directory tree style.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from logger.log_wrapper import get_logger

logger = get_logger("metrics:delegation", __name__)

@dataclass
class DelegationNode:
    """Represents a node in the delegation tree."""
    agent_name: str
    task_description: str
    status: str  # "pending", "completed", "failed"
    children: List['DelegationNode'] = field(default_factory=list)
    parent: Optional['DelegationNode'] = None
    timestamp: Optional[str] = None
    result: Optional[str] = None

class DelegationTracker:
    """Tracks delegation trees and generates tree-style output."""
    
    def __init__(self):
        self.root_delegations: List[DelegationNode] = []
        self.current_node: Optional[DelegationNode] = None
        self.delegation_stack: List[DelegationNode] = []
        self.root_agent: Optional[str] = None
    
    def _encode_newlines(self, text: str) -> str:
        """Encode newline characters so they do not break tree formatting."""
        # Encode Windows CRLF first to avoid partial double-encoding
        encoded = text.replace("\r\n", "\\n")
        # Encode remaining CR and LF
        encoded = encoded.replace("\r", "\\r").replace("\n", "\\n")
        return encoded
        
    def start_delegation(self, from_agent: str, to_agent: str, task_description: str, timestamp: str) -> None:
        """Start a new delegation."""
        # Set root agent if not already set
        if self.root_agent is None:
            self.root_agent = from_agent
        
        delegation_node = DelegationNode(
            agent_name=to_agent,
            task_description=task_description,
            status="pending",
            timestamp=timestamp
        )
        
        if self.current_node is None:
            # This is a root-level delegation
            self.root_delegations.append(delegation_node)
        else:
            # This is a nested delegation
            delegation_node.parent = self.current_node
            self.current_node.children.append(delegation_node)
        
        # Push onto stack and set as current
        self.delegation_stack.append(delegation_node)
        self.current_node = delegation_node
        
        logger.debug(f"Started delegation: {from_agent} -> {to_agent} ({task_description})")
    
    def complete_delegation(self, agent_name: str, result: str, timestamp: str) -> None:
        """Complete a delegation with result."""
        # Find the delegation in the stack
        for node in reversed(self.delegation_stack):
            if node.agent_name == agent_name and node.status == "pending":
                node.status = "completed"
                node.result = result
                logger.debug(f"Completed delegation: {agent_name} ({result[:50]}...)")
                # End the delegation to pop it from stack
                self.end_delegation(agent_name)
                return
        
        logger.warning(f"Attempted to complete delegation for {agent_name} but no matching pending delegation found")
    
    def fail_delegation(self, agent_name: str, error: str, timestamp: str) -> None:
        """Mark a delegation as failed."""
        # Find the delegation in the stack
        for node in reversed(self.delegation_stack):
            if node.agent_name == agent_name and node.status == "pending":
                node.status = "failed"
                node.result = f"Error: {error}"
                logger.debug(f"Failed delegation: {agent_name} ({error})")
                # End the delegation to pop it from stack
                self.end_delegation(agent_name)
                return
        
        logger.warning(f"Attempted to fail delegation for {agent_name} but no matching pending delegation found")
    
    def end_delegation(self, agent_name: str) -> None:
        """End the current delegation and pop from stack."""
        if self.delegation_stack and self.delegation_stack[-1].agent_name == agent_name:
            self.delegation_stack.pop()
            self.current_node = self.delegation_stack[-1] if self.delegation_stack else None
            logger.debug(f"Ended delegation: {agent_name}")
        else:
            logger.warning(f"Attempted to end delegation for {agent_name} but no matching delegation in stack")
    
    def get_tree_string(self, node: Optional[DelegationNode] = None, prefix: str = "", is_last: bool = True) -> str:
        """Generate a file directory style tree string for the delegation tree."""
        if node is None:
            # Start with root agent and delegations
            if not self.root_delegations:
                return "No delegations tracked"
            
            result = ""
            if self.root_agent:
                root_display = self._encode_newlines(self.root_agent)
                result += f"└── 🏠 {root_display}\n"
                for i, root_node in enumerate(self.root_delegations):
                    is_last_root = i == len(self.root_delegations) - 1
                    child_prefix = "    " if is_last_root else "│   "
                    result += self._format_node(root_node, child_prefix, is_last_root)
            else:
                for i, root_node in enumerate(self.root_delegations):
                    is_last_root = i == len(self.root_delegations) - 1
                    result += self._format_node(root_node, "", is_last_root)
            return result
        
        return self._format_node(node, prefix, is_last)
    
    def _format_node(self, node: DelegationNode, prefix: str, is_last: bool) -> str:
        """Format a single node in the tree."""
        # Status indicator
        status_icon = {
            "pending": "⏳",
            "completed": "✅",
            "failed": "❌"
        }.get(node.status, "❓")
        
        # Tree connector
        connector = "└── " if is_last else "├── "
        
        # Format the node with task description merged
        task_summary = ""
        if node.task_description:
            encoded_description = self._encode_newlines(node.task_description)
            task_summary = f" - {encoded_description[:50]}{'...' if len(encoded_description) > 50 else ''}"
        
        agent_display = self._encode_newlines(node.agent_name)
        result = f"{prefix}{connector}{status_icon} {agent_display}{task_summary}\n"
        
        # Add children
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            child_prefix = prefix + ("    " if is_last else "│   ")
            result += self._format_node(child, child_prefix, is_last_child)
        
        return result
    
    def save_delegation_tree(self, filepath: str) -> str:
        """Save the delegation tree to a file."""
        tree_content = self.get_tree_string()
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(tree_content)
        
        logger.info(f"Saved delegation tree to: {filepath}")
        return filepath
    
    def has_delegations(self) -> bool:
        """Check if any delegations have been tracked."""
        return len(self.root_delegations) > 0
    
    def get_delegation_summary(self) -> Dict[str, Any]:
        """Get a summary of delegation statistics."""
        def count_nodes(node: DelegationNode) -> Dict[str, int]:
            counts = {"total": 1, "completed": 0, "failed": 0, "pending": 0}
            counts[node.status] += 1
            
            for child in node.children:
                child_counts = count_nodes(child)
                for key in counts:
                    counts[key] += child_counts[key]
            
            return counts
        
        total_counts = {"total": 0, "completed": 0, "failed": 0, "pending": 0}
        
        for root_node in self.root_delegations:
            node_counts = count_nodes(root_node)
            for key in total_counts:
                total_counts[key] += node_counts[key]
        
        return {
            "total_delegations": total_counts["total"],
            "completed_delegations": total_counts["completed"],
            "failed_delegations": total_counts["failed"],
            "pending_delegations": total_counts["pending"],
            "has_delegations": self.has_delegations()
        } 