#!/usr/bin/env ./.venv/bin/python
"""
OrcAgent - Main Entry Point

Enterprise-grade orchestration of AI agents with AWS infrastructure integration.
Provides comprehensive logging, environment management, and structured workflow execution.
"""

import argparse
import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import autogen # type: ignore
from dotenv import load_dotenv # type: ignore

# Import agent environments and tools
from agent_environment.agent_environments import reset_environments
from agents.initial_agents import create_and_configure_agents
from logger.logging_config import setup_logging
from logger.log_wrapper import get_logger
from logger import dump_repository_on_exit
from metrics.metrics_tracker import MetricsTracker
from tools.tool_tracker import set_metrics_tracker
from configuration import INITIATOR_CHAT_MAX_ROUNDS, TIME_LIMIT_PROMPTS

load_dotenv(override=True)

logger = get_logger("main", __name__)

prompt_professionalism_suffix = """
\nEnsure all deliverables are reviewed/tested/verified in an iterative cycle to achieve a maximally professional degree of confidence before terminating.
"""

prompt_termination_suffix = """
\nIMPORTANT: 
- Don't ask any questions back, you are solely responsible/accountable that the tasks are completed without any user assistance, via using the tools provided, including delegation if available.
- When all tasks are fully complete, and only when every requirement is confidently verified as delivered, terminate your product delivery with the word 'TERMINATE'.
- Be sure not to reference TERMINATE at all, until actually wanting to terminate
- You have a time limit of {TIME_LIMIT_PROMPTS} units of time, measured as count of prompts (there will be a running clock in all prompts), to complete the task before automatic termination and immediate evaluation of deliverables as-is.
""".format(TIME_LIMIT_PROMPTS=TIME_LIMIT_PROMPTS)

def execute_agent_workflow(group_chat_manager: autogen.GroupChatManager, 
                          group_chat: autogen.GroupChat, 
                          root_initiator: autogen.Agent,
                          prompt: str, log_filename: str,
                          metrics_tracker: MetricsTracker) -> Dict[str, Any]:
    """
    Execute the agent workflow with comprehensive logging and error handling.
    
    Args:
        group_chat_manager: The group chat manager that orchestrates the conversation
        group_chat: The group chat configuration
        root_initiator: The user proxy agent that initiates the conversation
        prompt: User prompt to execute
        log_filename: Path to log file
        metrics_tracker: Metrics tracker for recording execution statistics
        
    Returns:
        Dict[str, Any]: Execution results and status
    """
    logger.info("Starting agent workflow execution with GroupChat")
    
    # Add agents to metrics tracking
    for agent in group_chat.agents:
        agent_type = getattr(agent, 'agent_type', 'unknown')
        metrics_tracker.add_agent(agent.name, agent_type)
    
    # Execute workflow
    try:
        with open(log_filename, 'a') as log_file:
            original_stdout = sys.stdout
            
            # Capture both stdout and logging
            class TeeStream:
                def __init__(self, *streams):
                    self.streams = streams
                
                def write(self, data):
                    for stream in self.streams:
                        stream.write(data)
                        stream.flush()
                
                def flush(self):
                    for stream in self.streams:
                        stream.flush()
            
            sys.stdout = TeeStream(original_stdout, log_file)
            
            try:
                # Log workflow initiation
                logger.info(f"WORKFLOW EXECUTION STARTED - Prompt: {prompt} - Timestamp: {datetime.now().isoformat()}")
                logger.info(f"Active group chat contains {len(group_chat.agents)} agents: {[agent.name for agent in group_chat.agents]}")
                
                # Add termination instructions to the prompt
                enhanced_prompt = prompt + prompt_termination_suffix
                
                # Initiate agent chat using root_initiator with group chat manager
                chat_result = root_initiator.initiate_chat(
                    group_chat_manager,
                    message=enhanced_prompt,
                    summary_method="reflection_with_llm",
                )
                
                # Log completion
                logger.info(f"WORKFLOW EXECUTION COMPLETED - Timestamp: {datetime.now().isoformat()}")
                
                # Check if initiator chat was cut short due to max rounds
                if len(group_chat.messages) >= INITIATOR_CHAT_MAX_ROUNDS:
                    metrics_tracker.record_initiator_chat_cut_short()
                    logger.warning(f"Initiator chat was cut short due to max rounds limit ({INITIATOR_CHAT_MAX_ROUNDS})")
                
                # Complete metrics tracking with success
                metrics_tracker.complete_execution(True)
                
                return {
                    'success': True,
                    'chat_result': chat_result,
                    'log_file': log_filename
                }
                
            finally:
                sys.stdout = original_stdout
                
    except Exception as e:
        import traceback
        from openai import RateLimitError
        
        # Complete metrics tracking with error
        error_message = str(e)
        metrics_tracker.complete_execution(False, error_message)
        
        if isinstance(e, RateLimitError):
            logger.error(f"Rate limit exceeded after all retries: {e}")
            return {
                'success': False,
                'error': f"Rate limit exceeded: {str(e)}",
                'log_file': log_filename,
                'traceback': traceback.format_exc(),
                'rate_limit_error': True
            }
        else:
            logger.error(f"Workflow execution failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'log_file': log_filename,
                'traceback': traceback.format_exc()
            }

def main(custom_prompt: Optional[str] = None, clean_env: bool = False, agents_mode: str = "team", model: str = "gpt-5") -> str:
    """
    Main function to orchestrate AI agents with AWS infrastructure integration.
    
    Args:
        custom_prompt: Custom prompt to use (required, no default prompt)
        clean_env: Whether to clean environments before running
        agents_mode: Agent initialization mode ('solo', 'pair', 'team', 'company', 'orchestrator', 'orchestrator-(small|medium|large)-(minimal|balanced|extensive)')
        model: LLM model to use (defaults to 'gpt-5')
        
    Returns:
        str: Path to the log file
    """
    # Setup run directory and logging
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_log_dir = f"../OrcAgent_runs/{timestamp}"
    
    # Setup logging
    log_filename = setup_logging(run_log_dir)

    logger.info(f"Initial flags received: prompt='{custom_prompt}', clean_env={clean_env}, agents_mode='{agents_mode}', model='{model}'")
    
    # Initialize metrics tracker
    metrics_tracker = MetricsTracker(run_log_dir)
    
    # Set up tool tracking
    set_metrics_tracker(metrics_tracker)
    
    try:
        if clean_env:
            reset_environments()
        
        # Configure LLM
        config_list = [
            {
                "model": model,
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "price": [0.0, 0.0]
            }
        ]
        
        # Create and configure agents with GroupChat setup
        group_chat_manager, group_chat, root_initiator = create_and_configure_agents(run_log_dir, config_list, mode=agents_mode)
        
        # No default prompt - require user to provide one
        if custom_prompt is None:
            logger.error("No prompt provided. Please provide a prompt using --prompt argument.")
            raise ValueError("No prompt provided. Please provide a prompt using --prompt argument.")
        
        # Start metrics tracking
        metrics_tracker.start_execution(model, agents_mode, custom_prompt)
        
        # Execute workflow using GroupChat
        result = execute_agent_workflow(group_chat_manager, group_chat, root_initiator, custom_prompt, log_filename, metrics_tracker)
        
        # Log final status
        if result['success']:
            logger.info(f"Agent workflow completed successfully! Results logged to: {log_filename}")
        else:
            logger.error(f"Agent workflow failed: {result.get('error', 'Unknown error')} - Error details logged to: {log_filename}")
        
        return log_filename
    
    finally:
        # Save metrics and delegation data on exit regardless of success/failure/exception
        try:
            metrics_filepath = metrics_tracker.save_metrics("metrics.json")
            logger.info(f"Metrics saved to: {metrics_filepath}")
        except Exception as e:
            logger.error(f"Failed to save metrics on exit: {e}")

        try:
            if metrics_tracker.has_delegations():
                delegation_filepath = metrics_tracker.save_delegation_tree("delegation_tree.txt")
                logger.info(f"Delegation tree saved to: {delegation_filepath}")
            else:
                logger.info("No delegations tracked, skipping delegation tree save")
        except Exception as e:
            logger.error(f"Failed to save delegation tree on exit: {e}")

        # Dump role and worker data on exit regardless of success/failure/exception
        logger.info("Dumping role and worker data on main exit...")
        dump_repository_on_exit(log_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OrcAgent - Enterprise Agent Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup.py                           # Set up infrastructure first
  python main.py --prompt "Deploy the application to AWS"
  python main.py --clean                    # Clean environments before use
  python main.py --prompt "Update documentation" --clean
  python main.py --prompt "Do everything" --agents=solo
  python main.py --prompt "Analyze code" --model=gpt-4o
        """
    )
    
    parser.add_argument(
        "--prompt", 
        type=str, 
        help="Prompt to send to the agents (required)",
        required=True
    )
    
    parser.add_argument(
        "--clean", 
        action="store_true",
        help="Clean all environments before running",
        default=False
    )
    
    parser.add_argument(
        "--agents",
        type=str,
        choices=["solo", "pair", "team", "company", "orchestrator", 
                 "orchestrator-small-minimal", "orchestrator-small-balanced", "orchestrator-small-extensive", 
                 "orchestrator-medium-minimal", "orchestrator-medium-balanced", "orchestrator-medium-extensive", 
                 "orchestrator-large-minimal", "orchestrator-large-balanced", "orchestrator-large-extensive"],
        default="team",
        help="Choose agent initialization mode: 'solo', 'pair', 'team', 'company', 'orchestrator', 'orchestrator-(small|medium|large)-(minimal|balanced|extensive)'"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5",
        help="LLM model to use (defaults to 'gpt-5')"
    )
    
    args = parser.parse_args()
    
    try:
        log_file = main(
            custom_prompt=args.prompt, 
            clean_env=args.clean,
            agents_mode=args.agents,
            model=args.model
        )
        print(f"\nExecution completed. Results logged to: {log_file}")
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        sys.exit(1) 