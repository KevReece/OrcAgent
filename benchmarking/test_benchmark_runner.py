#!/usr/bin/env python3
"""
Benchmark Runner Tests

Tests for benchmark runner functionality.
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from benchmarking.benchmark_runner import BenchmarkRunner
from benchmarking.benchmark_scenarios import create_benchmark_scenarios


class TestBenchmarkRunner(unittest.TestCase):
    """Test benchmark runner functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.runner = BenchmarkRunner(output_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_runner_initialization(self):
        """Test benchmark runner initialization."""
        self.assertIsNotNone(self.runner)
        self.assertEqual(self.runner.output_dir, Path(self.test_dir))
        # Check that the benchmark run directory and agent directory are created
        self.assertTrue(self.runner.benchmark_run_dir.exists())
        self.assertTrue(self.runner.agent_dir.exists())
    
    def test_get_available_scenarios(self):
        """Test getting available scenarios."""
        scenarios = self.runner.get_available_scenarios()
        
        self.assertIsInstance(scenarios, list)
        self.assertGreater(len(scenarios), 0)
        
        for scenario in scenarios:
            self.assertIn('id', scenario)
            self.assertIn('complexity', scenario)
            self.assertIn('initial_evaluations_count', scenario)
            self.assertIn('followup_evaluations_count', scenario)
    
    def test_get_scenario_details(self):
        """Test getting scenario details."""
        details = self.runner.get_scenario_details("solo-electrician-website")

        self.assertIsNotNone(details)
        self.assertEqual(details['id'], "solo-electrician-website")
        self.assertIn('complexity', details)
        self.assertIn('initial_prompt', details)
        self.assertIn('follow_up_prompt', details)
        self.assertIn('initial_evaluations', details)
        self.assertIn('followup_evaluations', details)
    
    def test_summary_data_generation(self):
        """Test summary data generation."""
        from benchmarking.benchmark_evaluator import ScenarioEvaluationResult
        
        # Create mock results
        mock_results = [
            ScenarioEvaluationResult(
                scenario_id="test-1",
                scenario_name="test-1",
                total_score=8.0,
                max_possible_score=10.0,
                passed_evaluations=5,
                total_evaluations=5,
                evaluation_results=[],
                execution_time_minutes=30.0,
                log_file_path="/tmp/test1.log",
                model_used="gpt-4.1-nano"
            ),
            ScenarioEvaluationResult(
                scenario_id="test-2",
                scenario_name="test-2",
                total_score=6.0,
                max_possible_score=10.0,
                passed_evaluations=3,
                total_evaluations=5,
                evaluation_results=[],
                execution_time_minutes=45.0,
                log_file_path="/tmp/test2.log",
                model_used="gpt-4o"
            )
        ]
        
        summary = self.runner._generate_summary_data(mock_results)
        
        self.assertIn('benchmark_run_id', summary)
        self.assertIn('agent_name', summary)
        self.assertIn('models_used', summary)
        self.assertIn('scenarios', summary)
        self.assertIn('statistics', summary)
        self.assertIn('complexity_breakdown', summary)
        
        # Check statistics
        stats = summary['statistics']
        self.assertEqual(stats['total_scenarios'], 2)
        self.assertEqual(stats['successful_scenarios'], 1)
        self.assertEqual(stats['failed_scenarios'], 1)
        self.assertEqual(stats['total_score'], 14.0)
        self.assertEqual(stats['max_possible_score'], 20.0)
        self.assertEqual(stats['average_score'], 7.0)
        self.assertEqual(stats['total_execution_time'], 75.0)
        self.assertEqual(stats['average_execution_time'], 37.5)
    
    def test_move_run_folders_both_initial_and_followup(self):
        """Test that both initial and follow-up run folders are moved correctly."""
        from benchmarking.benchmark_evaluator import ScenarioEvaluationResult
        
        # Create mock evaluation result
        mock_result = ScenarioEvaluationResult(
            scenario_id="test-scenario",
            scenario_name="test-scenario",
            total_score=8.0,
            max_possible_score=10.0,
            passed_evaluations=4,
            total_evaluations=5,
            evaluation_results=[],
            execution_time_minutes=30.0,
            log_file_path="/tmp/test.log",
            model_used="gpt-4.1-nano"
        )
        
        # Create mock initial and follow-up results
        initial_result = {
            'success': True,
            'log_file': '/tmp/OrcAgent_runs/20240101_120000/logs/orcagent_run.log',
            'stdout': 'Results logged to: /tmp/OrcAgent_runs/20240101_120000/logs/orcagent_run.log',
            'stderr': '',
            'returncode': 0,
            'execution_time': 15.0
        }
        
        follow_up_result = {
            'success': True,
            'log_file': '/tmp/OrcAgent_runs/20240101_120100/logs/orcagent_run.log',
            'stdout': 'Results logged to: /tmp/OrcAgent_runs/20240101_120100/logs/orcagent_run.log',
            'stderr': '',
            'returncode': 0,
            'execution_time': 15.0
        }
        
        # Mock the _move_single_run_folder method to track calls
        with patch.object(self.runner, '_move_single_run_folder') as mock_move:
            self.runner._move_run_folders_to_scenario(mock_result, initial_result, follow_up_result)
            
            # Verify that _move_single_run_folder was called twice (once for initial, once for follow-up)
            self.assertEqual(mock_move.call_count, 2)
            
            # Verify the calls were made with correct parameters
            calls = mock_move.call_args_list
            self.assertEqual(calls[0][0][0], self.runner.agent_dir / "test-scenario")  # scenario_dir
            self.assertEqual(calls[0][0][1], initial_result['log_file'])  # log_file_path
            self.assertEqual(calls[0][0][2], "initial")  # run_type
            
            self.assertEqual(calls[1][0][0], self.runner.agent_dir / "test-scenario")  # scenario_dir
            self.assertEqual(calls[1][0][1], follow_up_result['log_file'])  # log_file_path
            self.assertEqual(calls[1][0][2], "followup")  # run_type


if __name__ == "__main__":
    unittest.main() 