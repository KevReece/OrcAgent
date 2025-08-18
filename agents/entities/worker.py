"""
Worker Entity Class

This module defines the Worker class which represents worker instances of roles.
"""

import os
from typing import List, Dict, Any, Optional
import autogen
from dataclasses import dataclass, field
from logger.log_wrapper import get_logger
from .role import Role
from .associate import Associate
from tools.memory_tools import Memory
from configuration import INITIATOR_CHAT_MAX_ROUNDS, DELEGATION_CHAT_MAX_ROUNDS

logger = get_logger("agents:entities:worker", __name__)

# Global registry to track worker counts per role for auto-incrementing IDs
_role_worker_counts: Dict[str, int] = {}


@dataclass
class Worker:
    """
    Represents a worker instance of a role.
    
    This class combines a Role definition with worker-specific information
    like worker ID and associate relationships.
    
    Attributes:
        role: The Role this worker instantiates
        worker_id: Unique worker identifier within the role type (auto-incremented if not provided)
        associates: List of associate relationships for this worker
        is_initiator: Whether this worker is the initial/primary worker for group chats
        memory: Memory instance for storing prioritized memories
    """
    role: Role
    worker_id: Optional[int] = None
    _associates: List[Associate] = field(default_factory=list)
    is_initiator: bool = False
    _worker_agent: Optional[autogen.Agent] = field(default=None, repr=False)
    _executor_agent: Optional[autogen.Agent] = field(default=None, repr=False)
    memory: Memory = field(default_factory=Memory, repr=False)
    _run_dir: Optional[str] = field(default=None, repr=False)
    _config_list: Optional[List[Dict[str, Any]]] = field(default=None, repr=False)
    _is_integration_test: bool = field(default=False, repr=False)
    _tools_registered: bool = field(default=False, repr=False)
    _role_repository: Optional[Any] = field(default=None, repr=False)
    _associated_from: List[str] = field(default_factory=list, repr=False)
    
    def __post_init__(self) -> None:
        """Validate worker configuration and auto-assign worker_id if needed."""
        # Validate role first before attempting to use it
        if not isinstance(self.role, Role):
            raise ValueError("role must be a Role instance")
        
        # Auto-assign worker_id if not provided
        if self.worker_id is None:
            self.worker_id = self._get_next_worker_id()
        
        self._validate_worker()
        logger.debug(f"Created worker: {self.get_name()}")
    
    def initialize_runtime_config(self, run_dir: str, config_list: List[Dict[str, Any]], 
                                 is_integration_test: bool = False, role_repository: Optional[Any] = None) -> None:
        """
        Initialize runtime configuration for agent creation.
        
        Args:
            run_dir: Base directory for agent runs
            config_list: LLM configuration list
            is_integration_test: Whether running in integration test mode
            role_repository: Optional role repository for delegation tools
        """
        self._run_dir = run_dir
        self._config_list = config_list
        self._is_integration_test = is_integration_test
        self._role_repository = role_repository
    
    def store_memory(self, content: str, priority: int) -> str:
        """
        Store a memory and clear agents so they can be reinstantiated with updated memory.
        
        Args:
            content: Memory content
            priority: Priority value
            
        Returns:
            str: Success message
        """
        result = self.memory.store_memory(content, priority)
        if "Successfully stored" in result:
            self.clear_agents()
        return result
    
    def get_memories(self) -> List[tuple[str, int]]:
        """Get all stored memories ordered by priority."""
        return self.memory.get_memories()
    
    def clear_agents(self) -> None:
        """Clear worker and executor agents so they can be reinstantiated."""
        self._worker_agent = None
        self._executor_agent = None
        logger.debug(f"Cleared agents for worker {self.get_name()}")
    
    def get_worker_agent(self) -> Optional[autogen.Agent]:
        """Get worker agent, creating it lazily if needed."""
        if self._worker_agent is None:
            self._worker_agent = self._create_worker_agent()
            if self._worker_agent and self._executor_agent is None:
                self._executor_agent = self._create_worker_executor()
            if self._worker_agent and self._executor_agent:
                self._register_tools()
        return self._worker_agent
    
    def get_executor_agent(self) -> Optional[autogen.Agent]:
        """Get executor agent, creating it lazily if needed."""
        if self._executor_agent is None:
            self._executor_agent = self._create_worker_executor()
            if self._worker_agent and self._executor_agent:
                self._register_tools()
        return self._executor_agent
    
    def set_associates(self, associates: List[Associate]):
        """Set all associates for this worker."""
        self._associates = associates
        
    def set_associate(self, associate_worker: 'Worker') -> None:
        """
        Add an associate worker and maintain synchronization.
        
        Args:
            associate_worker: The worker to add as an associate
        """
        # Create Associate object with default relationship
        associate = Associate(name=associate_worker.get_name(), relationship="colleague")
        
        # Add to this worker's associates if not already present
        if not any(assoc.name == associate.name for assoc in self._associates):
            self._associates.append(associate)
        
        # Add this worker to the associate's _associated_from list
        if self.get_name() not in associate_worker._associated_from:
            associate_worker._associated_from.append(self.get_name())

    def _create_worker_agent(self) -> autogen.Agent:
        """Create worker agent for worker."""
        from agent_environment.agent_environments import setup_agent_working_directories
        
        if self._run_dir is None or self._config_list is None:
            raise ValueError("Worker not initialized with runtime config - call initialize_runtime_config() first")
        
        worker_name = self.get_name()
        work_dir = os.path.join(self._run_dir, "agent_work_dirs", worker_name)
        os.makedirs(work_dir, exist_ok=True)
        
        logger.info(f"Creating worker agent '{worker_name}' with work directory: {work_dir}")
        
        # Setup working directory
        if not setup_agent_working_directories([work_dir]):
            logger.error(f"Agent working directory setup failed for {worker_name}")
            raise Exception(f"Agent working directory setup failed for {worker_name}")
        
        # Configure llm_config
        llm_config = {"config_list": self._config_list}
        
        # Create agent with memory-enhanced instructions
        system_message = self.get_custom_instructions()
        
        from agents.rate_limited_agent import create_rate_limited_assistant_agent
        
        agent = create_rate_limited_assistant_agent(
            name=worker_name,
            system_message=system_message,
            llm_config=llm_config,
        )
        
        # Register agent with metrics tracker if available
        from tools.tool_tracker import _metrics_tracker
        if _metrics_tracker is not None:
            _metrics_tracker.add_agent(worker_name, "worker")
        
        logger.info(f"Created worker agent '{worker_name}'")
        return agent
    
    def _create_worker_executor(self) -> autogen.Agent:
        """Create worker executor for worker."""
        if self._run_dir is None:
            raise ValueError("Worker not initialized with runtime config - call initialize_runtime_config() first")
        
        worker_name = self.get_name()
        executor_name = f"{worker_name}_executor"
        executor_work_dir = os.path.join(self._run_dir, "agent_work_dirs", executor_name)
        os.makedirs(executor_work_dir, exist_ok=True)
        
        logger.info(f"Creating worker executor '{executor_name}' with work directory: {executor_work_dir}")
        
        from agents.rate_limited_agent import create_rate_limited_user_proxy_agent
        
        executor_agent = create_rate_limited_user_proxy_agent(
            name=executor_name,
            system_message=f"You are a worker executor for {worker_name}. You ONLY execute function calls - you should never respond to conversation messages or prompts. Only respond when executing a function call.",
            human_input_mode="NEVER",
            # Disable arbitrary code block execution; all actions must go through registered tools
            code_execution_config=False,
            max_consecutive_auto_reply=max(INITIATOR_CHAT_MAX_ROUNDS, DELEGATION_CHAT_MAX_ROUNDS),
            is_termination_msg=lambda msg: msg is not None and "TERMINATE" in (msg.get("content", "") or ""),
        )
        
        # Register executor agent with metrics tracker if available
        from tools.tool_tracker import _metrics_tracker
        if _metrics_tracker is not None:
            _metrics_tracker.add_agent(executor_name, "executor")
        
        logger.info(f"Created worker executor '{executor_name}'")
        return executor_agent
    
    def get_custom_instructions(self) -> str:
        """
        Generate custom instructions for this worker, including professional role expectations,
        associate details, and memories.
        
        Returns:
            str: Customized instructions for the worker agent.
        """
        professional_prefix = self._get_professional_role_instructions()
        
        base_instructions = self.role.base_instructions
        
        associates_instructions = ""
        if self._associates:
            associates_instructions += "\n\nAssociates:\n"
            associates_instructions += "You can delegate tasks to the following workers by their worker name using the delegate_to_worker tool:\n"
            for associate in self._associates:
                associates_instructions += f"- {associate.name}: {associate.relationship}\n"
            associates_instructions += "\nUse the delegate_to_worker tool when you need to collaborate with other team members.\n"
        
        memory_instructions = ""
        memories = self.memory.get_memories()
        if memories:
            memory_instructions += "\n\nMemories:\n"
            memory_instructions += "You have access to the following stored memories (ordered by priority):\n"
            for content, priority in memories:
                memory_instructions += f"- Priority {priority}: {content}\n"
        
        return professional_prefix + base_instructions + associates_instructions + memory_instructions

    def _get_professional_role_instructions(self) -> str:
        """
        Generate professional role instruction prefix for all workers.
        
        Returns:
            str: Professional role instruction prefix
        """
        return """
You are operating in a high-stakes business environment in the role of '{self.role.role_name}'.
You must assume your professional role to the full extent including strategic planning, tactical execution, auditability, 
comprehensive documentation, quality assurance, and mature delegation practices, and all role specific responsibilities. 
Establish clear roles and responsibilities across all available associates, then delegate and collaborate appropriately. 
Every action and deliverable must reflect enterprise-level excellence and contribute to the organization's strategic objectives.
"""

    def _get_next_worker_id(self) -> int:
        """Get the next available worker ID for this role."""
        role_name = self.role.role_name
        if role_name not in _role_worker_counts:
            _role_worker_counts[role_name] = 0
        
        _role_worker_counts[role_name] += 1
        return _role_worker_counts[role_name]
    
    def _validate_worker(self) -> None:
        """Validate required worker fields and constraints."""
        
        if self.worker_id is None or self.worker_id < 1:
            raise ValueError("worker_id must be >= 1")
        
        # Validate associates
        for i, associate in enumerate(self._associates):
            if not isinstance(associate, Associate):
                raise ValueError(f"Associate at index {i} must be an Associate instance")
    
    def get_name(self) -> str:
        """
        Generate unique name for this worker.
        
        Returns:
            str: Unique worker name in format {role_name}_{worker_id}
        """
        return f"{self.role.role_name}_{self.worker_id}"
    
    def clone(self, 
              new_worker_id: Optional[int] = None,
              new_role: Optional[Role] = None) -> 'Worker':
        """
        Create a clone of this worker with optional modifications.
        
        This is useful for creating multiple instances of the same role type
        with different worker IDs or role variations.
        
        Args:
            new_worker_id: Optional new worker ID for the clone
            new_role: Optional new role for the clone
            
        Returns:
            Worker: Cloned worker instance
        """
        clone = Worker(
            role=new_role or self.role,
            worker_id=new_worker_id,  # Will be auto-assigned if None
            is_initiator=False  # Clones are not initiators by default
        )
        
        # Copy associates using proper method
        if self._associates:
            clone.set_associates([Associate(assoc.name, assoc.relationship) for assoc in self._associates])
        
        # Copy runtime config
        if self._run_dir and self._config_list is not None:
            clone.initialize_runtime_config(self._run_dir, self._config_list, self._is_integration_test)
        
        logger.debug(f"Cloned worker '{self.get_name()}' to '{clone.get_name()}'")
        return clone
    
    def __str__(self) -> str:
        """String representation of the worker."""
        initiator_marker = " (initiator)" if self.is_initiator else ""
        memory_count = self.memory.get_memory_count()
        return f"Worker({self.role.role_name}, worker_{self.worker_id}{initiator_marker}, {memory_count} memories)"
    
    def __repr__(self) -> str:
        """Detailed string representation of the worker."""
        return (f"Worker(role='{self.role.role_name}', worker_id={self.worker_id}, "
                f"associates={len(self._associates)}, is_initiator={self.is_initiator}, "
                f"memories={self.memory.get_memory_count()})")
    
    def dump_to_json(self) -> Dict[str, Any]:
        """
        Generate JSON representation of this worker including role, associates, and memories.
        
        Returns:
            Dict[str, Any]: Complete worker data as JSON-serializable dictionary
        """
        # Serialize role data
        role_data = {
            "role_name": self.role.role_name,
            "base_instructions": self.role.base_instructions,
            "description": self.role.description,
            "role_version": self.role.role_version,
            "tool_group_names": self.role.tool_group_names
        }
        
        # Serialize associates
        associates_data = []
        for associate in self._associates:
            associates_data.append({
                "name": associate.name,
                "relationship": associate.relationship
            })
        
        # Serialize memories
        memories_data = []
        for content, priority in self.memory.get_memories():
            memories_data.append({
                "content": content,
                "priority": priority
            })
        
        # Build complete worker data
        worker_data = {
            "worker_name": self.get_name(),
            "worker_id": self.worker_id,
            "is_initiator": self.is_initiator,
            "role": role_data,
            "associates": associates_data,
            "memories": memories_data,
            "memory_count": self.memory.get_memory_count(),
            "has_worker_agent": self._worker_agent is not None,
            "has_executor_agent": self._executor_agent is not None,
            "tools_registered": self._tools_registered
        }
        
        return worker_data

    def _register_tools(self) -> None:
        """Register tools for this worker's agents."""
        if self._run_dir is None:
            raise ValueError("Worker not initialized with runtime config - call initialize_runtime_config() first")
        
        if not self._worker_agent or not self._executor_agent:
            return
        
        import importlib
        import autogen
        from typing import Any
        from tools.context import ToolsContext
        from tools.tool_tracker import track_tool_call
        
        worker_name = self.get_name()
        work_dir = os.path.join(self._run_dir, "agent_work_dirs", worker_name)
        
        # Gather tools for this worker
        tools: List[Any] = []
        if self.role.tool_group_names:
            logger.info(f"Gathering tools for {worker_name}")
            tool_group_module_prefix = "tools."
            
            tools_context = ToolsContext(
                role_repository=self._role_repository,
                self_worker_name=worker_name,
                agent_work_dir=work_dir,
                is_integration_test=self._is_integration_test
            )
            
            for tool_group_name in self.role.tool_group_names:
                module_name = tool_group_module_prefix + tool_group_name
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, 'get_tools'):
                        # Get the original tools (list of functions)
                        original_tools = module.get_tools(tools_context)
                        
                        # Apply tracking decorators to each tool function
                        tracked_tools = []
                        for tool_func in original_tools:
                            if callable(tool_func):
                                # Apply tracking decorator directly to the function
                                tracked_func = track_tool_call(tool_group_name, tool_func.__name__)(tool_func)
                                tracked_tools.append(tracked_func)
                            else:
                                # Keep non-callable items as-is
                                tracked_tools.append(tool_func)
                        
                        tools.extend(tracked_tools)
                        logger.info(f"Loaded and tracked tools from {tool_group_name} for {worker_name}")
                    else:
                        logger.warning(f"Tool module {tool_group_name} does not have a get_tools function.")
                except Exception as e:
                    logger.error(f"Failed to load tools from {tool_group_name} for {worker_name}: {e}")
        
        # Register tools with the agent-executor pair
        for tool in tools:
            try:
                autogen.register_function(
                    tool,
                    caller=self._worker_agent,
                    executor=self._executor_agent,
                    name=tool.__name__,
                    description=tool.__doc__ or f"Execute {tool.__name__}",
                )
            except Exception as e:
                logger.warning(f"Failed to register tool {tool.__name__} with {worker_name}: {e}")
        
        logger.info(f"Registered {len(tools)} tools with {worker_name} -> {self._executor_agent.name}")
        self._tools_registered = True

    def destroy(self, role_repository) -> None:
        """
        Clean up all references to this worker in associates and associated_from lists.
        Should be called before deleting the worker from the repository.
        Args:
            role_repository: The RoleRepository instance to look up other workers
        """
        # Remove this worker from all associates' _associated_from lists
        for associate in self._associates:
            associate_worker = role_repository.get_worker(associate.name)
            if associate_worker and self.get_name() in associate_worker._associated_from:
                associate_worker._associated_from.remove(self.get_name())
        # Remove all references to this worker in other workers' _associated_from lists
        for worker in role_repository.get_all_workers():
            if self.get_name() in worker._associated_from:
                worker._associated_from.remove(self.get_name())


def reset_worker_counts() -> None:
    """
    Reset worker counts for all roles. 
    
    This is primarily for testing purposes to ensure clean state.
    """
    global _role_worker_counts
    _role_worker_counts.clear()
    logger.debug("Reset all role worker counts")


def get_worker_count(role_name: str) -> int:
    """
    Get the current worker count for a specific role.
    
    Args:
        role_name: Name of the role
        
    Returns:
        int: Current worker count for the role
    """
    return _role_worker_counts.get(role_name, 0) 