#!/usr/bin/env python3
"""
Memory Tools Module

This module provides memory functionality for storing and retrieving prioritized memories.
"""

from typing import List, Dict, Tuple, Callable, Optional
from dataclasses import dataclass
import heapq
from logger.log_wrapper import get_logger
from tools.context import ToolsContext

logger = get_logger("tools:memory", __name__)


@dataclass
class MemoryEntry:
    """A single memory entry with content and priority."""
    content: str
    priority: int
    
    def __lt__(self, other: 'MemoryEntry') -> bool:
        """Compare entries by priority (lower priority = smaller for min heap)."""
        return self.priority < other.priority


class Memory:
    """
    Memory storage system that maintains the top 100 memories ordered by priority.
    
    Uses a min-heap to efficiently maintain only the highest priority memories.
    """
    
    def __init__(self, max_size: int = 20):
        """
        Initialize memory storage.
        
        Args:
            max_size: Maximum number of memories to store
        """
        self.max_size = max_size
        self._memories: List[MemoryEntry] = []
        logger.debug(f"Memory initialized with max_size: {max_size}")
    
    def store_memory(self, content: str, priority: int) -> str:
        """
        Store a memory with given priority, maintaining top memories only.
        
        Args:
            content: Memory content (limited string)
            priority: Priority value (higher numbers = higher priority)
            
        Returns:
            str: Success message
        """
        if not content or not content.strip():
            return "Error: Memory content cannot be empty"
        
        content = content.strip()
        if len(content) > 1000:
            content = content[:1000]
            logger.warning("Memory content truncated to 1000 characters")
        
        new_entry = MemoryEntry(content=content, priority=priority)
        
        if len(self._memories) < self.max_size:
            heapq.heappush(self._memories, new_entry)
        else:
            if priority > self._memories[0].priority:
                heapq.heapreplace(self._memories, new_entry)
            else:
                logger.debug(f"Memory with priority {priority} not stored (below threshold)")
                return f"Memory not stored (priority {priority} below current minimum)"
        
        logger.debug(f"Stored memory with priority {priority}")
        return f"Successfully stored memory with priority {priority}"
    
    def get_memories(self) -> List[Tuple[str, int]]:
        """
        Get all stored memories ordered by priority (highest first).
        
        Returns:
            List[Tuple[str, int]]: List of (content, priority) tuples ordered by priority
        """
        sorted_memories = sorted(self._memories, key=lambda x: x.priority, reverse=True)
        result = [(entry.content, entry.priority) for entry in sorted_memories]
        logger.debug(f"Retrieved {len(result)} memories")
        return result
    
    def clear(self) -> None:
        """Clear all stored memories."""
        self._memories.clear()
        logger.debug("Cleared all memories")
    
    def get_memory_count(self) -> int:
        """Get the current number of stored memories."""
        return len(self._memories)


def get_tools(tools_context: ToolsContext):
    """
    Get memory tools for an agent.
    Args:
        tools_context: ToolsContext instance
    Returns:
        List of tool functions
    """
    if not tools_context.role_repository or not tools_context.self_worker_name:
        return []
    worker = tools_context.role_repository.get_worker(tools_context.self_worker_name)
    if not worker:
        return []
    def store_memory(content: str, priority: int) -> str:
        return worker.store_memory(content, priority)
    def get_memories() -> list:
        return worker.get_memories()
    return [store_memory, get_memories] 