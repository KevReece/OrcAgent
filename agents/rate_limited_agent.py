#!/usr/bin/env python3
"""
Rate-Limited Agent Wrapper

Provides rate-limited versions of AutoGen agents with proper error handling.
"""

import autogen  # type: ignore
import tiktoken
from typing import Dict, Any, Optional
from openai import RateLimitError
from logger.rate_limit_handler import handle_rate_limit_with_retry
from logger.log_wrapper import get_logger
from configuration import API_TIMEOUT_SECONDS, TIME_LIMIT_PROMPTS
from tools.tool_tracker import _metrics_tracker, set_current_agent
from metrics.time_budget import annotate_and_maybe_terminate

logger = get_logger("rate_limited_agent", __name__)


class RateLimitedAssistantAgent(autogen.AssistantAgent):
    """
    Rate-limited version of AutoGen AssistantAgent.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f"Created rate-limited assistant agent: {self.name}")
    
    def generate_reply(self, messages=None, sender=None, **kwargs):
        """
        Generate reply with rate limit handling and timeout.
        """
        try:
            # Set current agent context for tool tracking
            set_current_agent(self.name)
            
            result = handle_rate_limit_with_retry(
                super().generate_reply, 
                messages=messages, 
                sender=sender, 
                timeout=API_TIMEOUT_SECONDS,  # 10 minute timeout
                **kwargs
            )
            try:
                if _metrics_tracker is not None:
                    model_name: Optional[str] = None
                    llm_cfg = getattr(self, "llm_config", None)
                    if isinstance(llm_cfg, dict):
                        cfg_list = llm_cfg.get("config_list")
                        if isinstance(cfg_list, list) and cfg_list and isinstance(cfg_list[0], dict):
                            model_name = cfg_list[0].get("model")

                    encoding = None
                    if model_name:
                        try:
                            encoding = tiktoken.encoding_for_model(model_name)
                        except Exception:
                            encoding = tiktoken.get_encoding("cl100k_base")
                    else:
                        encoding = tiktoken.get_encoding("cl100k_base")

                    output_text: str = ""
                    if isinstance(result, str):
                        output_text = result
                    elif isinstance(result, dict) and "content" in result:
                        content_val = result.get("content")
                        if isinstance(content_val, str):
                            output_text = content_val
                    elif hasattr(result, "content"):
                        content_attr = getattr(result, "content", None)
                        if isinstance(content_attr, str):
                            output_text = content_attr

                    tokens_used = len(encoding.encode(output_text)) if output_text else 0
                    # Record the response first to advance the prompt counter
                    _metrics_tracker.record_agent_response(self.name, tokens_used=tokens_used)

                    # Build time status and prepend to the outbound content
                    current_count = _metrics_tracker.metrics.total_agent_responses
                    result = annotate_and_maybe_terminate(
                        result=result,
                        current_count=current_count,
                        max_count=TIME_LIMIT_PROMPTS,
                        metrics_tracker=_metrics_tracker,
                    )
            except Exception as metric_err:
                logger.error(f"Failed to record agent response metrics for {self.name}: {metric_err}")

            return result
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded for agent {self.name}: {e}")
            raise e
        except TimeoutError as e:
            logger.error(f"Timeout exceeded for agent {self.name}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error generating reply for agent {self.name}: {e}")
            raise e


class RateLimitedUserProxyAgent(autogen.UserProxyAgent):
    """
    Rate-limited version of AutoGen UserProxyAgent.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f"Created rate-limited user proxy agent: {self.name}")
    
    def generate_reply(self, messages=None, sender=None, **kwargs):
        """
        Generate reply with rate limit handling and timeout.
        """
        try:
            # Set current agent context for tool tracking
            set_current_agent(self.name)
            
            result = handle_rate_limit_with_retry(
                super().generate_reply, 
                messages=messages, 
                sender=sender, 
                timeout=API_TIMEOUT_SECONDS,  # 10 minute timeout
                **kwargs
            )
            # Do not annotate or terminate from executors/user proxies; only main assistant handles tagging/termination
            return result
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded for agent {self.name}: {e}")
            raise e
        except TimeoutError as e:
            logger.error(f"Timeout exceeded for agent {self.name}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error generating reply for agent {self.name}: {e}")
            raise e


def create_rate_limited_assistant_agent(name: str, system_message: str, 
                                     llm_config: Dict[str, Any], **kwargs) -> RateLimitedAssistantAgent:
    """
    Create a rate-limited assistant agent.
    
    Args:
        name: Agent name
        system_message: System message
        llm_config: LLM configuration
        **kwargs: Additional arguments
        
    Returns:
        RateLimitedAssistantAgent: Configured agent
    """
    return RateLimitedAssistantAgent(
        name=name,
        system_message=system_message,
        llm_config=llm_config,
        **kwargs
    )


def create_rate_limited_user_proxy_agent(name: str, system_message: str = "",
                                       human_input_mode: str = "NEVER",
                                       code_execution_config: Any = False,
                                       max_consecutive_auto_reply: int = 0,
                                       **kwargs) -> RateLimitedUserProxyAgent:
    """
    Create a rate-limited user proxy agent.
    
    Args:
        name: Agent name
        system_message: System message
        human_input_mode: Human input mode
        code_execution_config: Code execution configuration
        max_consecutive_auto_reply: Max consecutive auto replies
        **kwargs: Additional arguments
        
    Returns:
        RateLimitedUserProxyAgent: Configured agent
    """
    return RateLimitedUserProxyAgent(
        name=name,
        system_message=system_message,
        human_input_mode=human_input_mode,
        code_execution_config=code_execution_config,
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        **kwargs
    ) 