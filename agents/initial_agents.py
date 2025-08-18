#!/usr/bin/env python3
"""
Dynamic Agent Configuration Module

This module provides functionality to create and configure AutoGen agents dynamically
based on initial JSON configuration, with GroupChat setup for orchestration.
"""

from typing import Tuple, List, Dict, Any
import autogen # type: ignore
from dotenv import load_dotenv
from logger.log_wrapper import get_logger
from configuration import INITIATOR_CHAT_MAX_ROUNDS

load_dotenv(override=True)

logger = get_logger("agents:dynamic", __name__)

def _create_user_proxy_agent() -> autogen.UserProxyAgent:
    logger.info("Creating main user proxy agent")
    from agents.rate_limited_agent import create_rate_limited_user_proxy_agent
    
    user_proxy = create_rate_limited_user_proxy_agent(
        name="root_initiator",
        system_message="",
        human_input_mode="NEVER",
        code_execution_config=False,
        max_consecutive_auto_reply=0,
    )
    logger.info("User proxy agent created successfully")
    return user_proxy

def _setup_group_chat_for_initiator(repository, config_list: List[Dict[str, Any]], mode: str) -> Tuple[autogen.GroupChatManager, autogen.GroupChat, autogen.Agent]:
    """
    Common setup for group chat with a single initiator worker.
    
    Args:
        repository: The configured role repository
        config_list: LLM configuration list
        mode: The agent mode for logging purposes
        
    Returns:
        Tuple[autogen.GroupChatManager, autogen.GroupChat, autogen.Agent]: 
        Group chat manager, group chat, and root user proxy agent
    """
    initiator_worker = repository.get_initial_worker()
    if not initiator_worker:
        raise ValueError(f"No initiator worker found in repository for mode: {mode}")
    
    worker_name = initiator_worker.get_name()
    worker_agent = repository.get_worker_agent(worker_name)
    worker_executor = repository.get_worker_executor(worker_name)
    
    if not worker_agent or not worker_executor:
        raise ValueError(f"Worker agent or executor not found for {worker_name} in mode: {mode}")
    
    root_agent = _create_user_proxy_agent()
    group_chat = autogen.GroupChat(
        agents=[worker_agent, worker_executor],
        messages=[],
        max_round=INITIATOR_CHAT_MAX_ROUNDS,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=True,
    )
    group_chat_manager = autogen.GroupChatManager(
        groupchat=group_chat,
        llm_config={"config_list": config_list},
        system_message="",
    )
    logger.info(f"Successfully created {mode} agent group chat with initiator: {worker_name}")
    return group_chat_manager, group_chat, root_agent

def create_and_configure_agents(run_dir: str, config_list: List[Dict[str, Any]], mode: str = "team") -> Tuple[autogen.GroupChatManager, autogen.GroupChat, autogen.Agent]:
    """
    Create and configure agents in a group chat setup, supporting team, solo, pair, orchestrator, and company modes.
    Args:
        run_dir: Base directory for the agent run
        config_list: LLM configuration list
        mode: 'team' (default), 'solo', 'pair', 'orchestrator', or 'company'
    Returns:
        Tuple[autogen.GroupChatManager, autogen.GroupChat, autogen.Agent]: 
        Group chat manager, group chat, and root user proxy agent
    """
    logger.info(f"Starting agent configuration process for mode: {mode}")
    
    # Setup repository based on mode
    if mode == "solo":
        from agents.definitions.solo_agent_definition import setup_solo_repository
        repository = setup_solo_repository(run_dir, config_list, is_integration_test=False)
    elif mode == "pair":
        from agents.definitions.agent_pair_definition import setup_agent_pair_repository
        repository = setup_agent_pair_repository(run_dir, config_list, is_integration_test=False)
    elif mode.startswith("orchestrator"):
        from agents.definitions.orchestrator_agent_definition import setup_orchestrator_repository
        organization_size = mode.split("-")[1] if len(mode.split("-")) > 1 else "dynamic"
        role_description_complexity = mode.split("-")[2] if len(mode.split("-")) > 2 else "balanced"
        repository = setup_orchestrator_repository(run_dir, config_list, organization_size=organization_size, role_description_complexity=role_description_complexity, is_integration_test=False)
    elif mode == "company":
        from agents.definitions.company_definition import setup_company_repository
        repository = setup_company_repository(run_dir, config_list, is_integration_test=False)
    else:  # team (default)
        from agents.definitions.team_definition import setup_default_repository
        repository = setup_default_repository(run_dir, config_list, is_integration_test=False)
    
    # Use common group chat setup for all modes (single initiator)
    return _setup_group_chat_for_initiator(repository, config_list, mode) 