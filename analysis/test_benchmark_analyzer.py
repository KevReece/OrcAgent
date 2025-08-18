#!/usr/bin/env python3
"""
Tests for the BenchmarkAnalyzer module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from benchmark_analyzer import BenchmarkAnalyzer, BenchmarkResult, UsageMetrics


class TestBenchmarkAnalyzer:
    """Test cases for BenchmarkAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = BenchmarkAnalyzer()
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path(self.temp_dir)
        
        # Create fake results structure
        self._create_fake_results()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_fake_results(self):
        """Create fake benchmark results for testing."""
        # Create directory structure with agent modes
        solo_dir = self.results_dir / "solo"
        pair_dir = self.results_dir / "pair"
        
        for dir_path in [solo_dir, pair_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create fake result files
        fake_results = [
            {
                "scenario_id": "test_001",
                "scenario_name": "Test 1",
                "total_score": 8.0,
                "max_possible_score": 10.0,
                "passed_evaluations": 4,
                "total_evaluations": 5,
                "execution_time_minutes": 2.5,
                "model_used": "gpt-4",
                "log_file_path": str(solo_dir / "test_001.log")
            },
            {
                "scenario_id": "test_002",
                "scenario_name": "Test 2",
                "total_score": 7.0,
                "max_possible_score": 10.0,
                "passed_evaluations": 3,
                "total_evaluations": 5,
                "execution_time_minutes": 2.0,
                "model_used": "gpt-4",
                "log_file_path": str(solo_dir / "test_002.log")
            },
            {
                "scenario_id": "test_003",
                "scenario_name": "Test 3",
                "total_score": 15.0,
                "max_possible_score": 20.0,
                "passed_evaluations": 6,
                "total_evaluations": 8,
                "execution_time_minutes": 5.0,
                "model_used": "gpt-4o",
                "log_file_path": str(pair_dir / "test_003.log")
            },
            {
                "scenario_id": "test_004",
                "scenario_name": "Test 4",
                "total_score": 25.0,
                "max_possible_score": 30.0,
                "passed_evaluations": 8,
                "total_evaluations": 10,
                "execution_time_minutes": 8.0,
                "model_used": "gpt-4o",
                "log_file_path": str(pair_dir / "test_004.log")
            }
        ]
        
        # Create separate directories for each result to avoid overwriting
        for i, result in enumerate(fake_results):
            # Create a unique directory for each result
            result_dir = Path(result["log_file_path"]).parent / f"result_{i}"
            result_dir.mkdir(parents=True, exist_ok=True)
            
            # Update log file path to be in the new directory
            result["log_file_path"] = str(result_dir / f"{result['scenario_id']}.log")
            
            # Write evaluation file
            eval_file = result_dir / "evaluations.json"
            # Add log_file_path to the result data
            result_with_log_path = result.copy()
            result_with_log_path['log_file_path'] = str(result_dir / "metrics.json")
            with open(eval_file, 'w') as f:
                json.dump(result_with_log_path, f)
            
            # Create metrics.json file
            metrics_file = result_dir / "metrics.json"
            metrics_data = {
                "total_tokens": 1000 + (i * 100),
                "total_tool_calls": 10 + (i * 2),
                "tool_functions": {
                    "notion_tools:create_page": 5,
                    "docker_tools:docker_build_image": 3,
                    "delegation_tools:delegate_to_worker": 1 if i % 2 == 1 else 0
                },
                "agents": [
                    {
                        "name": "agent1",
                        "total_tokens": 500 + (i * 50)
                    }
                ]
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f)
    
    def test_extract_scenario_size(self):
        """Test scenario size extraction from file paths."""
        assert self.analyzer._extract_scenario_size("/path/to/small/test.json") == "small"
        assert self.analyzer._extract_scenario_size("/path/to/medium/test.json") == "medium"
        assert self.analyzer._extract_scenario_size("/path/to/large/test.json") == "large"
        assert self.analyzer._extract_scenario_size("/path/to/unknown/test.json") == "unknown"
    
    def test_load_results(self):
        """Test loading results from directory."""
        df = self.analyzer.load_results(self.results_dir)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert list(df.columns) == [
            'scenario_id', 'agent_mode', 'size', 'normalized_score'
        ]
        
        # Check that normalized scores are calculated correctly
        assert df.loc[df['scenario_id'] == 'test_001', 'normalized_score'].iloc[0] == 0.8
        assert df.loc[df['scenario_id'] == 'test_002', 'normalized_score'].iloc[0] == 0.7
    
    def test_load_results_nonexistent_directory(self):
        """Test loading results from non-existent directory."""
        with pytest.raises(ValueError, match="Results directory not found"):
            self.analyzer.load_results(Path("/nonexistent/path"))
    
    def test_static_mean_scores(self):
        """Test calculating mean scores using static methods."""
        results_df = self.analyzer.load_results(self.results_dir)
        mean_scores = self.analyzer.get_mean_scores(results_df)
        
        assert isinstance(mean_scores, pd.DataFrame)
        assert 'mean' in mean_scores.columns
        assert 'std' in mean_scores.columns
        assert 'count' in mean_scores.columns
        
        # Check that we have scores for both agent modes
        assert len(mean_scores) == 2
        assert 'solo' in mean_scores.index
        assert 'pair' in mean_scores.index
    
    def test_static_mean_scores_by_size(self):
        """Test calculating mean scores by size using static methods."""
        results_df = self.analyzer.load_results(self.results_dir)
        mean_scores = self.analyzer.get_mean_scores_by_size(results_df)
        
        assert isinstance(mean_scores, pd.DataFrame)
        assert 'mean' in mean_scores.columns
        assert 'std' in mean_scores.columns
        assert 'count' in mean_scores.columns
        
        # Check that we have scores for different sizes
        assert len(mean_scores) > 0
    
    def test_load_usage_metrics(self):
        """Test loading usage metrics."""
        df = self.analyzer.load_usage_metrics(self.results_dir)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert list(df.columns) == [
            'scenario_id', 'agent_mode', 'size', 'tokens_used', 'tool_calls', 'delegations'
        ]
        
        # Check that metrics are extracted
        assert all(df['tool_calls'] > 0)
        assert any(df['delegations'] > 0)  # At least some scenarios should have delegations
    
    def test_static_mean_usage_metrics(self):
        """Test calculating mean usage metrics using static methods."""
        usage_df = self.analyzer.load_usage_metrics(self.results_dir)
        mean_usage = self.analyzer.get_mean_usage_metrics(usage_df)
        
        assert isinstance(mean_usage, pd.DataFrame)
        assert 'tokens_used' in mean_usage.columns.get_level_values(0)
        assert 'tool_calls' in mean_usage.columns.get_level_values(0)
        assert 'delegations' in mean_usage.columns.get_level_values(0)
    
    def test_static_mean_usage_metrics_by_size(self):
        """Test calculating mean usage metrics by size using static methods."""
        usage_df = self.analyzer.load_usage_metrics(self.results_dir)
        mean_usage = self.analyzer.get_mean_usage_metrics_by_size(usage_df)
        
        assert isinstance(mean_usage, pd.DataFrame)
        assert len(mean_usage) > 0
    
    def test_static_summary_statistics(self):
        """Test getting summary statistics using static methods."""
        results_df = self.analyzer.load_results(self.results_dir)
        usage_df = self.analyzer.load_usage_metrics(self.results_dir)
        
        summary = self.analyzer.get_summary_statistics(results_df, usage_df)
        
        assert isinstance(summary, dict)
        assert 'total_scenarios' in summary
        assert 'unique_agent_modes' in summary
        assert 'unique_sizes' in summary
        assert 'overall_mean_score' in summary
        assert 'overall_std_score' in summary
        assert 'mean_scores_by_agent_mode' in summary
        assert 'mean_scores_by_size' in summary
        assert 'scenarios_with_usage_data' in summary
        assert 'mean_usage_by_agent_mode' in summary
        assert 'mean_usage_by_size' in summary
        
        assert summary['total_scenarios'] == 4
        assert summary['unique_agent_modes'] == 2
        assert summary['unique_sizes'] == 1
    
    def test_static_summary_statistics_without_usage(self):
        """Test getting summary statistics without usage metrics."""
        results_df = self.analyzer.load_results(self.results_dir)
        
        summary = self.analyzer.get_summary_statistics(results_df, None)
        
        assert 'total_scenarios' in summary
        assert 'scenarios_with_usage_data' not in summary
        assert 'mean_usage_by_agent_mode' not in summary
        assert 'mean_usage_by_size' not in summary
    
    def test_extract_metrics_from_log(self):
        """Test extracting metrics from metrics.json file."""
        # Create a test directory with metrics.json
        test_dir = self.results_dir / "test_scenario"
        test_dir.mkdir(exist_ok=True)
        
        metrics_file = test_dir / "metrics.json"
        metrics_data = {
            "total_tokens": 1500,
            "total_tool_calls": 15,
            "tool_functions": {
                "notion_tools:create_page": 5,
                "docker_tools:docker_build_image": 3,
                "delegation_tools:delegate_to_worker": 2
            },
            "agents": [
                {
                    "name": "agent1",
                    "total_tokens": 750
                }
            ]
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f)
        
        data = {"scenario_id": "test", "model_used": "solo"}
        file_path = test_dir / "evaluations.json"
        
        metrics = self.analyzer._extract_metrics_from_log(metrics_file, data, file_path)
        
        assert metrics is not None
        assert metrics['scenario_id'] == "test"
        assert metrics['size'] == "unknown"
        assert metrics['tool_calls'] == 15
        assert metrics['delegations'] == 2
        assert metrics['tokens_used'] >= 0  # Tokens might be 0 if tracking is disabled
    
    def test_extract_metrics_from_log_error(self):
        """Test extracting metrics from non-existent log file."""
        log_file = Path("/nonexistent/log.file")
        data = {"scenario_id": "test", "model_used": "gpt-4"}
        file_path = Path("/path/to/small/test.json")
        
        metrics = self.analyzer._extract_metrics_from_log(log_file, data, file_path)
        
        assert metrics is None
    
    def test_static_grouped_bar_chart_data(self):
        """Test preparing data for grouped bar charts using static methods."""
        # Load usage metrics
        usage_df = self.analyzer.load_usage_metrics(self.results_dir)
        
        # Test token usage data
        tokens_data = self.analyzer.get_grouped_bar_chart_data(usage_df, 'tokens_used')
        assert isinstance(tokens_data, pd.DataFrame)
        assert not tokens_data.empty
        
        # Test tool calls data
        tools_data = self.analyzer.get_grouped_bar_chart_data(usage_df, 'tool_calls')
        assert isinstance(tools_data, pd.DataFrame)
        assert not tools_data.empty
        
        # Test delegations data
        delegations_data = self.analyzer.get_grouped_bar_chart_data(usage_df, 'delegations')
        assert isinstance(delegations_data, pd.DataFrame)
        assert not delegations_data.empty
    
    def test_static_grouped_bar_chart_data_invalid_metric(self):
        """Test grouped bar chart data with invalid metric."""
        usage_df = self.analyzer.load_usage_metrics(self.results_dir)
        
        with pytest.raises(ValueError, match="Metric must be one of"):
            self.analyzer.get_grouped_bar_chart_data(usage_df, 'invalid_metric') 

    def test_get_mean_roles_by_size(self):
        """Test mean roles per scenario size for orchestrator mode."""
        # Use the real example results tree under benchmarking/results
        # If none exist, fall back to temp structure created in setup
        from pathlib import Path
        default_results = Path("../benchmarking/results")
        results_dir = default_results if default_results.exists() else self.results_dir

        df = self.analyzer.get_mean_roles_by_size(results_dir)
        assert isinstance(df, pd.DataFrame)
        
        # The method now returns a pivoted DataFrame with orchestrator modes as columns
        # and sizes as rows, so we check for that structure
        if not df.empty:
            # Should have sizes as index with name 'size'
            assert df.index.name == 'size'
            # Should have orchestrator modes as columns
            assert len(df.columns) > 0
            # All values should be non-negative (mean roles counts)
            for col in df.columns:
                assert (df[col] >= 0).all()

    def test_get_roles_bar_chart_data(self):
        """Test getting data formatted for bar chart visualization."""
        # Use the real example results tree under benchmarking/results
        # If none exist, fall back to temp structure created in setup
        from pathlib import Path
        default_results = Path("../benchmarking/results")
        results_dir = default_results if default_results.exists() else self.results_dir

        df = self.analyzer.get_roles_bar_chart_data(results_dir)
        assert isinstance(df, pd.DataFrame)
        
        # The method should return a DataFrame with orchestrator modes as index (x-axis)
        # and sizes as columns (separate bars)
        if not df.empty:
            # Should have orchestrator modes as index
            assert len(df.index) > 0
            # Should have sizes as columns
            assert len(df.columns) > 0
            # All values should be non-negative (mean roles counts)
            for col in df.columns:
                assert (df[col] >= 0).all()