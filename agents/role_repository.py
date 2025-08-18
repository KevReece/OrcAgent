"""
Role Repository Module

This module contains the RoleRepository singleton class for centralized management
of roles, workers, and their associated agents in the OrcAgent project.
"""

from typing import List, Dict, Any, Optional, Tuple
import autogen  # type: ignore
from logger.log_wrapper import get_logger
from agents.entities import Role, Worker, Associate
from datetime import datetime

logger = get_logger("agents:role_repository", __name__)


class RoleRepository:
    """
    Singleton repository for managing roles, workers, and their associated agents.
    
    This class provides centralized management of:
    - Role definitions by role name
    - Worker instances by agent name
    """
    
    _instance: Optional['RoleRepository'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'RoleRepository':
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the repository (only once due to singleton pattern)."""
        if self._initialized:
            return
        
        self._roles_by_name: Dict[str, Role] = {}
        self._workers_by_agent_name: Dict[str, Worker] = {}
        self._run_dir: Optional[str] = None
        self._config_list: Optional[List[Dict[str, Any]]] = None
        self._is_integration_test: bool = False
        self._initialized = True
        
        logger.info("Initialized RoleRepository singleton")
    
    def initialize(self, run_dir: str, config_list: List[Dict[str, Any]], 
                   is_integration_test: bool = False) -> None:
        """
        Initialize the repository with runtime configuration.
        
        Args:
            run_dir: Base directory for agent runs
            config_list: LLM configuration list
            is_integration_test: Whether running in integration test mode
        """
        self._run_dir = run_dir
        self._config_list = config_list
        self._is_integration_test = is_integration_test
        logger.info(f"Repository initialized with run_dir: {run_dir}")
    
    def register_role(self, role: Role) -> None:
        """
        Register a role definition in the repository.
        
        Args:
            role: Role to register
        """
        if role.role_name in self._roles_by_name:
            logger.warning(f"Role '{role.role_name}' already exists, overwriting")
        
        self._roles_by_name[role.role_name] = role
        logger.info(f"Registered role: {role.role_name}")
    
    def register_worker(self, worker: Worker) -> None:
        """
        Register a worker in the repository without spawning agents.
        
        Args:
            worker: Worker to register
        """
        worker_name = worker.get_name()
        if worker_name in self._workers_by_agent_name:
            logger.warning(f"Worker '{worker_name}' already exists, overwriting")
        
        self._workers_by_agent_name[worker_name] = worker
        logger.info(f"Registered worker: {worker_name}")
    
    def create_worker(self, role_name: str, 
                     associates: Optional[List[Tuple[str, str]]] = None,
                     is_initiator: bool = False) -> Worker:
        """
        Create a worker instance from a role with lazy agent creation.
        
        Args:
            role_name: Name of the role to instantiate
            associates: Optional list of (name, relationship) tuples
            is_initiator: Whether this worker is the group chat initiator
            
        Returns:
            Worker: The created worker instance
            
        Raises:
            ValueError: If role not found or configuration invalid
        """
        if not self._run_dir or not self._config_list:
            raise ValueError("Repository not initialized - call initialize() first")
        
        # Get the role definition
        if role_name not in self._roles_by_name:
            raise ValueError(f"Role '{role_name}' not found in repository")
        
        role = self._roles_by_name[role_name]
        
        # Create worker instance with auto-incrementing ID
        worker = Worker(role=role, is_initiator=is_initiator)
        
        # Initialize worker with runtime configuration for lazy agent creation
        worker.initialize_runtime_config(self._run_dir, self._config_list, self._is_integration_test, self)
        
        # Register worker
        self.register_worker(worker)
        
        # Set up associates after worker is registered
        if associates:
            worker_associates = []
            for name, relationship in associates:
                worker_associates.append(Associate(name=name, relationship=relationship))
            worker.set_associates(worker_associates)
            
            # Update _associated_from for all associate workers
            for name, _ in associates:
                associate_worker = self.get_worker(name)
                if associate_worker and worker.get_name() not in associate_worker._associated_from:
                    associate_worker._associated_from.append(worker.get_name())
        
        logger.info(f"Created worker '{worker.get_name()}' with lazy agent creation")
        return worker
    
    def create_worker_with_memories(self, role_name: str, memories: List[Tuple[str, int]], 
                                   is_initiator: bool = False, associates: Optional[List[Tuple[str, str]]] = None) -> Worker:
        """
        Create a worker with bootstrap memories.
        
        Args:
            role_name: Name of the role to create worker from
            memories: List of (content, priority) tuples for bootstrap memories
            is_initiator: Whether this worker is an initiator
            associates: List of (name, relationship) tuples for associates
            
        Returns:
            Worker: The created worker with bootstrap memories
        """
        worker = self.create_worker(
            role_name=role_name,
            associates=associates,
            is_initiator=is_initiator
        )
        
        # Add bootstrap memories
        for content, priority in memories:
            worker.store_memory(content, priority)
        
        return worker
    
    def get_role(self, role_name: str) -> Optional[Role]:
        """Get role by name."""
        return self._roles_by_name.get(role_name)
    
    def get_worker(self, worker_name: str) -> Optional[Worker]:
        """Get worker by worker name."""
        return self._workers_by_agent_name.get(worker_name)
    
    def get_worker_agent(self, worker_name: str) -> Optional[autogen.Agent]:
        """Get worker agent for worker, creating lazily if needed."""
        worker = self.get_worker(worker_name)
        if worker:
            return worker.get_worker_agent()
        return None
    
    def get_worker_executor(self, worker_name: str) -> Optional[autogen.Agent]:
        """Get worker executor for worker, creating lazily if needed."""
        worker = self.get_worker(worker_name)
        if worker:
            return worker.get_executor_agent()
        return None
    
    def get_initial_worker(self) -> Optional[Worker]:
        """
        Get the worker marked as initiator for group chat startup.
        
        Returns:
            Worker: The initiator worker, or None if no initiator is set
        """
        for worker in self._workers_by_agent_name.values():
            if worker.is_initiator:
                return worker
        return None
    
    def get_all_roles(self) -> List[Role]:
        """Get all registered roles."""
        return list(self._roles_by_name.values())
    
    def get_all_workers(self) -> List[Worker]:
        """Get all registered workers."""
        return list(self._workers_by_agent_name.values())
    
    def get_workers_by_role(self, role_name: str) -> List[Worker]:
        """Get all workers for a given role."""
        return [
            worker for worker in self._workers_by_agent_name.values()
            if worker.role.role_name == role_name
        ]
    
    def delete_worker(self, worker_name: str) -> bool:
        """
        Delete a worker from the repository.
        
        Args:
            worker_name: Name of the worker to delete
            
        Returns:
            bool: True if worker was deleted, False if not found
        """
        worker = self._workers_by_agent_name.get(worker_name)
        if worker:
            worker.destroy(self)
            del self._workers_by_agent_name[worker_name]
            logger.info(f"Deleted worker: {worker_name}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all repository data (useful for testing)."""
        self._roles_by_name.clear()
        self._workers_by_agent_name.clear()
        logger.info("Cleared repository data")
    
    def dump_repository_to_json(self) -> Dict[str, Any]:
        """
        Generate comprehensive JSON data for the entire repository including all roles, workers, and memories.
        
        Returns:
            Dict[str, Any]: Comprehensive JSON data containing the complete repository state
        """
        timestamp = datetime.now().isoformat()
        
        # Serialize all role definitions
        roles_data = {}
        for role_name, role in self._roles_by_name.items():
            roles_data[role_name] = {
                "role_name": role.role_name,
                "base_instructions": role.base_instructions,
                "description": role.description,
                "role_version": role.role_version,
                "tool_group_names": role.tool_group_names
            }
        
        # Serialize all workers using their own JSON dump method
        workers_data = {}
        for worker_name, worker in self._workers_by_agent_name.items():
            workers_data[worker_name] = worker.dump_to_json()
        
        repository_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "repository_type": "RoleRepository",
            "summary": {
                "total_roles": len(self._roles_by_name),
                "total_workers": len(self._workers_by_agent_name),
                "total_memories": sum(len(worker.get_memories()) for worker in self._workers_by_agent_name.values())
            },
            "roles": roles_data,
            "workers": workers_data
        }
        
        logger.info(f"Generated repository JSON data for {len(self._roles_by_name)} roles and {len(self._workers_by_agent_name)} workers")
        return repository_data

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        cls._instance = None
        cls._initialized = False 