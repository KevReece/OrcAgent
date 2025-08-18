#!/usr/bin/env python3
"""
Metrics Tracking Module

Tracks and logs execution metrics for agent workflows including:
- Model information
- Agent details
- Token usage
- Agent responses
- Tool calls and usage statistics
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from logger.log_wrapper import get_logger
from metrics.delegation_tracker import DelegationTracker

logger = get_logger("metrics:tracker", __name__)

@dataclass
class ToolCallMetrics:
    """Metrics for individual tool calls."""
    tool_name: str
    tool_group: str
    function_name: str
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0

@dataclass
class AgentMetrics:
    """Metrics for individual agents."""
    agent_name: str
    agent_type: str
    response_count: int = 0
    total_tokens: int = 0
    tool_calls: int = 0

@dataclass
class ExecutionMetrics:
    """Complete execution metrics."""
    timestamp: str
    model: str
    agents_mode: str
    prompt: str
    agents: List[Dict[str, Any]]
    tool_groups: Dict[str, int]
    tool_functions: Dict[str, int]
    total_tokens: int = 0
    total_agent_responses: int = 0
    total_tool_calls: int = 0
    success: bool = False
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    initiator_chat_cut_short: bool = False
    delegation_limit_reached: bool = False
    delegation_chat_max_rounds_reached_count: int = 0
    time_limit_prompts_reached: bool = False

class MetricsTracker:
    """Tracks and logs execution metrics for agent workflows."""
    
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.metrics = ExecutionMetrics(
            timestamp=datetime.now().isoformat(),
            model="",
            agents_mode="",
            prompt="",
            agents=[],
            tool_groups={},
            tool_functions={}
        )
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.tool_metrics: Dict[str, ToolCallMetrics] = {}
        self.start_time: Optional[datetime] = None
        self.delegation_tracker = DelegationTracker()
        
    def start_execution(self, model: str, agents_mode: str, prompt: str) -> None:
        """Start tracking execution metrics."""
        self.start_time = datetime.now()
        self.metrics.model = model
        self.metrics.agents_mode = agents_mode
        self.metrics.prompt = prompt
        logger.info(f"Started metrics tracking for model: {model}, mode: {agents_mode}")
        
    def add_agent(self, agent_name: str, agent_type: str) -> None:
        """Add an agent to tracking."""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentMetrics(
                agent_name=agent_name,
                agent_type=agent_type
            )
            self.metrics.agents.append({
                "name": agent_name,
                "type": agent_type,
                "response_count": 0,
                "total_tokens": 0,
                "tool_calls": 0
            })
            logger.debug(f"Added agent to tracking: {agent_name} ({agent_type})")
    
    def record_agent_response(self, agent_name: str, tokens_used: int = 0) -> None:
        """Record an agent response."""
        if agent_name in self.agent_metrics:
            self.agent_metrics[agent_name].response_count += 1
            self.agent_metrics[agent_name].total_tokens += tokens_used
            self.metrics.total_agent_responses += 1
            self.metrics.total_tokens += tokens_used
            
            # Update the agents list
            for agent in self.metrics.agents:
                if agent["name"] == agent_name:
                    agent["response_count"] += 1
                    agent["total_tokens"] += tokens_used
                    break
                    
            logger.debug(f"Recorded response for agent: {agent_name} (tokens: {tokens_used})")
    
    def record_tool_call(self, tool_name: str, function_name: str, success: bool = True) -> None:
        """Record a tool call."""
        tool_key = f"{tool_name}:{function_name}"
        
        if tool_key not in self.tool_metrics:
            # Determine tool group based on tool name
            tool_group = self._get_tool_group(tool_name)
            self.tool_metrics[tool_key] = ToolCallMetrics(
                tool_name=tool_name,
                tool_group=tool_group,
                function_name=function_name
            )
        
        self.tool_metrics[tool_key].call_count += 1
        if success:
            self.tool_metrics[tool_key].success_count += 1
        else:
            self.tool_metrics[tool_key].error_count += 1
        
        # Update tool groups
        tool_group = self.tool_metrics[tool_key].tool_group
        self.metrics.tool_groups[tool_group] = self.metrics.tool_groups.get(tool_group, 0) + 1
        
        # Update tool functions
        self.metrics.tool_functions[tool_key] = self.metrics.tool_functions.get(tool_key, 0) + 1
        
        self.metrics.total_tool_calls += 1
        logger.debug(f"Recorded tool call: {tool_name}.{function_name} (success: {success})")
    
    def record_agent_tool_call(self, agent_name: str) -> None:
        """Record a tool call for a specific agent."""
        if agent_name in self.agent_metrics:
            self.agent_metrics[agent_name].tool_calls += 1
            
            # Update the agents list
            for agent in self.metrics.agents:
                if agent["name"] == agent_name:
                    agent["tool_calls"] += 1
                    break
                    
            logger.debug(f"Recorded tool call for agent: {agent_name}")
        else:
            logger.warning(f"Attempted to record tool call for unknown agent: {agent_name}")
    
    def _get_tool_group(self, tool_name: str) -> str:
        """Determine tool group based on tool name."""
        tool_name_lower = tool_name.lower()
        
        # Check more specific patterns first
        if "github" in tool_name_lower:
            return "github"
        elif "git" in tool_name_lower:
            return "git"
        elif "docker" in tool_name_lower:
            return "docker"
        elif "aws" in tool_name_lower:
            return "aws"
        elif "notion" in tool_name_lower:
            return "notion"
        elif "file" in tool_name_lower:
            return "file"
        elif "memory" in tool_name_lower:
            return "memory"
        elif "delegation" in tool_name_lower:
            return "delegation"
        elif "orchestration" in tool_name_lower:
            return "orchestration"
        else:
            return "other"
    
    def complete_execution(self, success: bool, error_message: Optional[str] = None) -> None:
        """Complete execution and calculate final metrics."""
        if self.start_time:
            self.metrics.execution_time_seconds = (datetime.now() - self.start_time).total_seconds()
        
        self.metrics.success = success
        self.metrics.error_message = error_message
        
        # Update final agent metrics
        for agent_name, agent_metric in self.agent_metrics.items():
            for agent in self.metrics.agents:
                if agent["name"] == agent_name:
                    agent["response_count"] = agent_metric.response_count
                    agent["total_tokens"] = agent_metric.total_tokens
                    agent["tool_calls"] = agent_metric.tool_calls
                    break
        
        logger.info(f"Completed metrics tracking - Success: {success}, Total tokens: {self.metrics.total_tokens}, Total responses: {self.metrics.total_agent_responses}, Total tool calls: {self.metrics.total_tool_calls}")
    
    def save_metrics(self, filename: str = "metrics.json") -> str:
        """Save metrics to JSON file."""
        filepath = os.path.join(self.run_dir, filename)
        
        # Convert to dict and save
        metrics_dict = asdict(self.metrics)
        
        with open(filepath, 'w') as f:
            json.dump(metrics_dict, f, indent=2)
        
        logger.info(f"Saved metrics to: {filepath}")
        return filepath
    
    def save_delegation_tree(self, filename: str = "delegation_tree.txt") -> str:
        """Save delegation tree to a text file."""
        filepath = os.path.join(self.run_dir, filename)
        return self.delegation_tracker.save_delegation_tree(filepath)
    
    def start_delegation(self, from_agent: str, to_agent: str, task_description: str) -> None:
        """Start tracking a delegation."""
        timestamp = datetime.now().isoformat()
        self.delegation_tracker.start_delegation(from_agent, to_agent, task_description, timestamp)
    
    def complete_delegation(self, agent_name: str, result: str) -> None:
        """Complete a delegation with result."""
        timestamp = datetime.now().isoformat()
        self.delegation_tracker.complete_delegation(agent_name, result, timestamp)
    
    def fail_delegation(self, agent_name: str, error: str) -> None:
        """Mark a delegation as failed."""
        timestamp = datetime.now().isoformat()
        self.delegation_tracker.fail_delegation(agent_name, error, timestamp)
    
    def end_delegation(self, agent_name: str) -> None:
        """End a delegation."""
        self.delegation_tracker.end_delegation(agent_name)
    
    def has_delegations(self) -> bool:
        """Check if any delegations have been tracked."""
        return self.delegation_tracker.has_delegations()
    
    def get_delegation_summary(self) -> Dict[str, Any]:
        """Get delegation summary statistics."""
        return self.delegation_tracker.get_delegation_summary()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current metrics."""
        return {
            "model": self.metrics.model,
            "agents_mode": self.metrics.agents_mode,
            "total_tokens": self.metrics.total_tokens,
            "total_agent_responses": self.metrics.total_agent_responses,
            "total_tool_calls": self.metrics.total_tool_calls,
            "success": self.metrics.success,
            "execution_time_seconds": self.metrics.execution_time_seconds
        }
    
    def record_initiator_chat_cut_short(self) -> None:
        """Record that the initiator chat was cut short due to max rounds."""
        self.metrics.initiator_chat_cut_short = True
        logger.info("Recorded initiator chat cut short due to max rounds")
    
    def record_delegation_limit_reached(self) -> None:
        """Record that the delegation limit was reached."""
        self.metrics.delegation_limit_reached = True
        logger.info("Recorded delegation limit reached")
    
    def record_delegation_chat_max_rounds_reached(self) -> None:
        """Record that a delegation chat reached max rounds."""
        self.metrics.delegation_chat_max_rounds_reached_count += 1
        logger.info(f"Recorded delegation chat max rounds reached (count: {self.metrics.delegation_chat_max_rounds_reached_count})") 

    def record_time_limit_prompts_reached(self) -> None:
        """Record that the time limit measured in prompts was reached."""
        self.metrics.time_limit_prompts_reached = True
        logger.info("Recorded time limit prompts reached")