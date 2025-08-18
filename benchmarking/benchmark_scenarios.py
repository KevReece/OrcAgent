#!/usr/bin/env python3
"""
Benchmark Scenarios Module

Defines comprehensive benchmark scenarios for testing agent performance
across different complexity levels and domains.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import json

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), 'scenarios')

class ScenarioComplexity(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"
    TEST = "test"

@dataclass
class EvaluationStep:
    step: int
    action: str
    expected: str
    value: float

@dataclass
class Evaluation:
    name: str
    description: str
    initial_page: str
    steps: List[EvaluationStep]

@dataclass
class BenchmarkScenario:
    id: str
    complexity: ScenarioComplexity
    initial_prompt: str
    follow_up_prompt: str
    initial_evaluations: List[Evaluation]
    followup_evaluations: List[Evaluation]

def _load_prompt(scenario_id: str, prompt_type: str) -> str:
    # Find the scenario file in the appropriate complexity subdirectory
    # Explicitly check all complexity levels in order
    complexity_dirs = ["small", "medium", "large", "enterprise", "test"]
    for complexity_dir in complexity_dirs:
        complexity_path = os.path.join(SCENARIOS_DIR, complexity_dir)
        if os.path.exists(complexity_path):
            filename = f"{scenario_id}_{prompt_type}.md"
            file_path = os.path.join(complexity_path, filename)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    return f.read().strip()
    raise FileNotFoundError(f"Could not find {scenario_id}_{prompt_type}.md in any complexity subdirectory")

def _load_evaluations(scenario_id: str, evaluation_type: str) -> List[Evaluation]:
    """Load evaluation files for a scenario and evaluation type (initial or followup)."""
    evaluations = []
    
    # Find the scenario file in the appropriate complexity subdirectory
    # Explicitly check all complexity levels in order
    complexity_dirs = ["small", "medium", "large", "enterprise", "test"]
    for complexity_dir in complexity_dirs:
        complexity_path = os.path.join(SCENARIOS_DIR, complexity_dir)
        if os.path.exists(complexity_path):
            # Look for evaluation files with the pattern {scenario_id}_{evaluation_type}_evaluation*.json
            for filename in os.listdir(complexity_path):
                if filename.startswith(f"{scenario_id}_{evaluation_type}_evaluation") and filename.endswith('.json'):
                    file_path = os.path.join(complexity_path, filename)
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    # Convert JSON data to Evaluation object
                    steps = [EvaluationStep(**step) for step in data['steps']]
                    evaluation = Evaluation(
                        name=data['name'],
                        description=data['description'],
                        initial_page=data['initial_page'],
                        steps=steps
                    )
                    evaluations.append(evaluation)
    
    if not evaluations:
        raise FileNotFoundError(f"Could not find any {scenario_id}_{evaluation_type}_evaluation*.json files in any complexity subdirectory")
    
    return evaluations

def _scenario_complexity_from_id(scenario_id: str) -> ScenarioComplexity:
    # Find which complexity subdirectory contains this scenario
    # Explicitly check all complexity levels in order
    complexity_dirs = ["small", "medium", "large", "enterprise", "test"]
    for complexity_dir in complexity_dirs:
        complexity_path = os.path.join(SCENARIOS_DIR, complexity_dir)
        if os.path.exists(complexity_path):
            # Check if any file with this scenario_id exists in this complexity directory
            for filename in os.listdir(complexity_path):
                if filename.startswith(f"{scenario_id}_"):
                    return ScenarioComplexity(complexity_dir)
    raise ValueError(f"Unknown scenario id: {scenario_id}")

def _list_scenario_ids() -> List[str]:
    ids = set()
    # Look through all complexity subdirectories explicitly
    complexity_dirs = ["small", "medium", "large", "enterprise", "test"]
    for complexity_dir in complexity_dirs:
        complexity_path = os.path.join(SCENARIOS_DIR, complexity_dir)
        if os.path.exists(complexity_path):
            for fname in os.listdir(complexity_path):
                if fname.endswith('_initial.md'):
                    ids.add(fname.replace('_initial.md', ''))
    return sorted(ids)

def create_benchmark_scenarios() -> List[BenchmarkScenario]:
    scenarios: List[BenchmarkScenario] = []
    for scenario_id in _list_scenario_ids():
        complexity = _scenario_complexity_from_id(scenario_id)
        initial_prompt = _load_prompt(scenario_id, 'initial')
        follow_up_prompt = _load_prompt(scenario_id, 'followup')
        initial_evaluations = _load_evaluations(scenario_id, 'initial')
        followup_evaluations = _load_evaluations(scenario_id, 'followup')
        scenarios.append(BenchmarkScenario(
            id=scenario_id,
            complexity=complexity,
            initial_prompt=initial_prompt,
            follow_up_prompt=follow_up_prompt,
            initial_evaluations=initial_evaluations,
            followup_evaluations=followup_evaluations
        ))
    return scenarios

def get_scenario_by_id(scenario_id: str) -> Optional[BenchmarkScenario]:
    for scenario in create_benchmark_scenarios():
        if scenario.id == scenario_id:
            return scenario
    return None

def get_scenarios_by_complexity(complexity: ScenarioComplexity) -> List[BenchmarkScenario]:
    return [s for s in create_benchmark_scenarios() if s.complexity == complexity] 