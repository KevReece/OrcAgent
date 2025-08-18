#!/usr/bin/env python3
"""
Delegation Tools Module

This module provides tools for delegating tasks to other agents in the system.
"""

import autogen  # type: ignore
from logger.log_wrapper import get_logger
from tools.context import ToolsContext
from configuration import DELEGATION_LIMIT, DELEGATION_CHAT_MAX_ROUNDS
from tools.tool_tracker import _metrics_tracker

logger = get_logger("tools:delegation", __name__)


class DelegationTools:
    """Tools for delegating tasks to other agents in the system."""
    
    def __init__(self, tools_context: ToolsContext):
        """
        Initialize delegation tools.
        
        Args:
            agent_work_dir: Working directory for the agent
            role_repository: RoleRepository instance for accessing agents
            self_worker_name: Name of the worker that will use these tools
        """
        self.agent_work_dir = tools_context.agent_work_dir
        self.role_repository = tools_context.role_repository
        self.self_worker_name = tools_context.self_worker_name
        self.delegation_count = 0  # Track delegation count
        logger.info(f"DelegationTools initialized for {self.self_worker_name}")
    
    def delegate_to_worker(self, target_worker_name: str, task_description: str) -> str:
        """
        Delegate a task to a specific worker.
        
        Args:
            target_worker_name: Name of the worker to delegate to (e.g. 'systems_engineer_1')
            task_description: Description of the task to delegate
            
        Returns:
            str: Result of the delegation
        """
        # Check delegation limit
        if self.delegation_count >= DELEGATION_LIMIT:
            error_msg = f"Delegation limit of {DELEGATION_LIMIT} reached. Cannot perform more delegations."
            logger.error(error_msg)
            
            # Track delegation limit reached
            if _metrics_tracker is not None:
                try:
                    _metrics_tracker.record_delegation_limit_reached()
                except Exception as e:
                    logger.error(f"Failed to track delegation limit reached: {e}")
            
            return error_msg
        
        self.delegation_count += 1
        logger.info(f"Delegating task to worker '{target_worker_name}' (delegation #{self.delegation_count}): {task_description}")
        
        # Track delegation start
        if _metrics_tracker is not None:
            try:
                _metrics_tracker.start_delegation(self.self_worker_name, target_worker_name, task_description)
            except Exception as e:
                logger.error(f"Failed to track delegation start: {e}")
        
        # Get target worker from repository
        target_worker = self.role_repository.get_worker(target_worker_name)
        
        if not target_worker:
            all_workers = [worker.get_name() for worker in self.role_repository.get_all_workers()]
            error_msg = f"Worker '{target_worker_name}' not found. Available workers: {all_workers}"
            logger.error(error_msg)
            return error_msg
        
        # Use the first available worker for the role
        target_agent = target_worker.get_worker_agent()
        target_executor = target_worker.get_executor_agent()
        
        if not target_agent:
            error_msg = f"Worker agent for worker '{target_worker.get_name()}' not found"
            logger.error(error_msg)
            return error_msg
            
        if not target_executor:
            error_msg = f"Worker executor for worker '{target_worker.get_name()}' not found"
            logger.error(error_msg)
            return error_msg
        
        # Prepare delegation message with requestor details
        requestor_info = f"[DELEGATION FROM {self.self_worker_name}]: "
        delegation_message = requestor_info + task_description + """
\nNote:
- Respond with 'TERMINATE' to end this delegation when the task is fully complete or when more context is required.
- All tasks have an implicit expectation of synchronous completion including comprehensive verification and comprehensive evidence of completion. 
"""
        
        logger.info(f"Creating delegation group chat with {target_agent.name} and {target_executor.name}")
        
        try:
            # Create temporary group chat with target agent and its executor
            delegation_agents = [target_agent, target_executor]
            
            delegation_group_chat = autogen.GroupChat(
                agents=delegation_agents,
                messages=[],
                max_round=DELEGATION_CHAT_MAX_ROUNDS,
                speaker_selection_method="round_robin",
                allow_repeat_speaker=True,
            )
            
            # Create group chat manager for delegation
            delegation_manager = autogen.GroupChatManager(
                groupchat=delegation_group_chat,
            )
            
            # Get self agent from repository
            self_agent = self.role_repository.get_worker_agent(self.self_worker_name)

            if not self_agent:
                error_msg = f"Could not find self-agent '{self.self_worker_name}' for delegation"
                logger.error(error_msg)
                return error_msg
            
            # Initiate delegation conversation
            self_agent.initiate_chat(
                delegation_manager,
                message=delegation_message,
                summary_method="reflection_with_llm",
                is_termination_msg=lambda msg: msg is not None and "TERMINATE" in (msg.get("content", "") or ""),
            )
            
            # Extract result from the delegation group chat's last message instead of chat_result.summary
            delegation_result = "No result available"
            if delegation_group_chat.messages:
                # Get the last message from the group chat
                last_message = delegation_group_chat.messages[-1]
                if isinstance(last_message, dict) and "content" in last_message:
                    delegation_result = last_message["content"]
                elif hasattr(last_message, 'content'):
                    delegation_result = last_message.content
                else:
                    delegation_result = str(last_message)
            
            # Check if delegation chat reached max rounds
            if len(delegation_group_chat.messages) >= DELEGATION_CHAT_MAX_ROUNDS:
                if _metrics_tracker is not None:
                    try:
                        _metrics_tracker.record_delegation_chat_max_rounds_reached()
                    except Exception as e:
                        logger.error(f"Failed to track delegation chat max rounds reached: {e}")
                logger.warning(f"Delegation chat to {target_worker_name} reached max rounds limit ({DELEGATION_CHAT_MAX_ROUNDS})")
            
            result = f"Delegation to {target_worker_name} completed. Result: {delegation_result}"
            
            # Track delegation completion
            if _metrics_tracker is not None:
                try:
                    _metrics_tracker.complete_delegation(target_worker_name, delegation_result)
                except Exception as e:
                    logger.error(f"Failed to track delegation completion: {e}")
            
            logger.info(f"Delegation to {target_worker_name} completed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error during delegation to {target_worker_name}: {str(e)}"
            
            # Track delegation failure
            if _metrics_tracker is not None:
                try:
                    _metrics_tracker.fail_delegation(target_worker_name, str(e))
                except Exception as tracking_error:
                    logger.error(f"Failed to track delegation failure: {tracking_error}")
            
            logger.error(error_msg)
            return error_msg


def get_tools(tools_context: ToolsContext):
    """
    Get delegation tools for an agent.
    
    Args:
        tools_context: ToolsContext instance
        
    Returns:
        List of tool functions
    """
    if not tools_context.role_repository or not tools_context.self_worker_name:
        logger.warning("Delegation tools require role_repository and self_worker_name - returning empty list")
        return []
    
    logger.info(f"Creating delegation tools for agent {tools_context.self_worker_name}")
    
    delegation_tools = DelegationTools(tools_context)
    
    # Create a wrapper function around the delegate method
    def delegate_to_worker(target_worker_name: str, message: str) -> str:
        """
        Delegate a task to another worker by creating a temporary group chat.
        
        Args:
            target_worker_name: Name of the target worker to delegate to (e.g., 'systems_engineer_1')
            message: The task message to send to the worker
            
        Returns:
            str: Result of the delegation
        """
        return delegation_tools.delegate_to_worker(target_worker_name, message)
    
    return [
        delegate_to_worker,
    ] 