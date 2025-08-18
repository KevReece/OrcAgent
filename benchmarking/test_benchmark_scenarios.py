#!/usr/bin/env python3
"""
Benchmark Scenarios Tests

Tests for benchmark scenario definitions and management.
"""

import unittest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from benchmarking.benchmark_scenarios import (
    create_benchmark_scenarios, 
    get_scenario_by_id, 
    ScenarioComplexity,
    BenchmarkScenario,
    Evaluation,
    EvaluationStep
)


class TestBenchmarkScenarios(unittest.TestCase):
    """Test benchmark scenario definitions and management."""
    
    def test_create_benchmark_scenarios(self):
        """Test that benchmark scenarios are created correctly."""
        scenarios = create_benchmark_scenarios()
        
        self.assertIsInstance(scenarios, list)
        self.assertGreater(len(scenarios), 0)
        
        for scenario in scenarios:
            self.assertIsInstance(scenario, BenchmarkScenario)
            self.assertTrue(scenario.id)
            self.assertIsInstance(scenario.complexity, ScenarioComplexity)
            self.assertTrue(scenario.initial_prompt)
            self.assertTrue(scenario.follow_up_prompt)
            self.assertIsInstance(scenario.initial_evaluations, list)
            self.assertIsInstance(scenario.followup_evaluations, list)
            self.assertGreater(len(scenario.initial_evaluations), 0)
            self.assertGreater(len(scenario.followup_evaluations), 0)
    
    def test_scenario_complexity_distribution(self):
        """Test that scenarios are distributed across complexity levels."""
        scenarios = create_benchmark_scenarios()
        
        complexity_counts = {}
        for scenario in scenarios:
            complexity = scenario.complexity.value
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        # Should have scenarios in all complexity levels
        self.assertIn('small', complexity_counts)
        self.assertIn('medium', complexity_counts)
        self.assertIn('large', complexity_counts)
        self.assertIn('enterprise', complexity_counts)
        self.assertIn('test', complexity_counts)
        
        # Should have at least 1 scenario per complexity level
        for count in complexity_counts.values():
            self.assertGreaterEqual(count, 1)
    
    def test_get_scenario_by_id(self):
        """Test retrieving scenarios by ID."""
        # Test existing scenario
        scenario = get_scenario_by_id("solo-electrician-website")
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.id, "solo-electrician-website")
        
        # Test non-existent scenario
        scenario = get_scenario_by_id("non-existent-scenario")
        self.assertIsNone(scenario)
    
    def test_evaluation_structure(self):
        """Test that evaluations are properly structured."""
        scenarios = create_benchmark_scenarios()
        
        for scenario in scenarios:
            # Test initial evaluations
            for evaluation in scenario.initial_evaluations:
                self.assertIsInstance(evaluation, Evaluation)
                self.assertTrue(evaluation.name)
                self.assertTrue(evaluation.description)
                self.assertTrue(evaluation.initial_page)
                self.assertIsInstance(evaluation.steps, list)
                self.assertGreater(len(evaluation.steps), 0)
                
                for step in evaluation.steps:
                    self.assertIsInstance(step, EvaluationStep)
                    self.assertIsInstance(step.step, int)
                    self.assertTrue(step.action)
                    self.assertTrue(step.expected)
                    self.assertIsInstance(step.value, float)
                    self.assertGreater(step.value, 0)
            
            # Test followup evaluations
            for evaluation in scenario.followup_evaluations:
                self.assertIsInstance(evaluation, Evaluation)
                self.assertTrue(evaluation.name)
                self.assertTrue(evaluation.description)
                self.assertTrue(evaluation.initial_page)
                self.assertIsInstance(evaluation.steps, list)
                self.assertGreater(len(evaluation.steps), 0)
                
                for step in evaluation.steps:
                    self.assertIsInstance(step, EvaluationStep)
                    self.assertIsInstance(step.step, int)
                    self.assertTrue(step.action)
                    self.assertTrue(step.expected)
                    self.assertIsInstance(step.value, float)
                    self.assertGreater(step.value, 0)


if __name__ == "__main__":
    unittest.main() 