#!/usr/bin/env python3
"""
Benchmark Analysis Module

Provides functionality for loading and analyzing benchmark results.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import pandas as pd
import logging

def get_logger(name, module):
    """Simple logger function for testing."""
    return logging.getLogger(f"{name}.{module}")


@dataclass
class BenchmarkResult:
    """Represents a single benchmark result with minimal visualization data."""
    scenario_id: str
    agent_mode: str
    size: str
    normalized_score: float


@dataclass
class UsageMetrics:
    """Represents usage metrics for a benchmark run."""
    scenario_id: str
    agent_mode: str
    size: str
    tokens_used: int
    tool_calls: int
    delegations: int


class BenchmarkAnalyzer:
    """Analyzes benchmark results and provides statistical insights."""
    
    def __init__(self):
        self.logger = get_logger("benchmark:analyzer", __name__)
    
    @staticmethod
    def load_results(results_dir: Path) -> pd.DataFrame:
        """
        Load evaluation results files into a pandas DataFrame.
        
        Args:
            results_dir: Path to the results directory
            
        Returns:
            DataFrame containing all benchmark results
        """
        if not results_dir.exists():
            raise ValueError(f"Results directory not found: {results_dir}")
        
        logger = get_logger("benchmark:analyzer", "load_results")
        logger.info(f"Loading results from: {results_dir}")
        
        results = []
        
        # Look for evaluation results files specifically
        for file_path in results_dir.glob("**/evaluations.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Check if this is a valid evaluation result file
                    required_fields = ['scenario_id', 'scenario_name', 'total_score', 
                                    'max_possible_score', 'passed_evaluations', 'total_evaluations',
                                    'execution_time_minutes', 'model_used']
                    
                    if not all(field in data for field in required_fields):
                        logger.warning(f"Skipping {file_path}: missing required fields")
                        continue
                    
                    # Extract scenario size and agent mode from path
                    size = BenchmarkAnalyzer._extract_scenario_size(str(file_path))
                    agent_mode = BenchmarkAnalyzer._extract_agent_mode(str(file_path))
                    
                    # Calculate normalized score
                    normalized_score = data['total_score'] / data['max_possible_score']
                    
                    # Create result object with minimal data for visualizations
                    result = BenchmarkResult(
                        scenario_id=data['scenario_id'],
                        agent_mode=agent_mode,  # Agent mode derived from path
                        size=size,
                        normalized_score=normalized_score
                    )
                    
                    # Convert to dict for DataFrame
                    results.append({
                        'scenario_id': result.scenario_id,
                        'agent_mode': result.agent_mode,
                        'size': result.size,
                        'normalized_score': result.normalized_score
                    })
                    
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        results_df = pd.DataFrame(results)
        logger.info(f"Loaded {len(results_df)} results")
        
        return results_df
    
    @staticmethod
    def _extract_scenario_size(file_path: str) -> str:
        """Determine scenario size (complexity) from results path by mapping scenario id to scenarios tree.

        Strategy:
        - Derive scenario_id from the parent directory name of the evaluations.json path
        - Look under benchmarking/scenarios/<size>/ for files that start with that scenario_id
        - Return the matching <size> directory name if found; otherwise 'unknown'
        """
        try:
            eval_path = Path(file_path)
            scenario_id_from_path = eval_path.parent.name

            project_root = Path(__file__).resolve().parents[1]
            scenarios_root = project_root / 'benchmarking' / 'scenarios'

            if scenarios_root.exists():
                size_dirs = ['test', 'small', 'medium', 'large', 'enterprise']
                for size_dir in size_dirs:
                    candidate_dir = scenarios_root / size_dir
                    if not candidate_dir.exists():
                        continue
                    # Look for markdown or json definitions that start with the scenario_id
                    pattern_md = f"{scenario_id_from_path}_*.md"
                    pattern_json = f"{scenario_id_from_path}_*.json"
                    has_md = any(candidate_dir.glob(pattern_md))
                    has_json = any(candidate_dir.glob(pattern_json))
                    if has_md or has_json:
                        return size_dir
        except Exception:
            # Fall through to path keyword scan or unknown
            pass

        # Fallback: inspect directory parts only, prefer a real size dir over filename tokens
        dir_parts = [p.lower() for p in Path(file_path).parts[:-1]]  # exclude filename
        for keyword in ['small', 'medium', 'large', 'enterprise', 'test']:
            if keyword in dir_parts:
                return keyword

        return 'unknown'
    
    @staticmethod
    def _extract_agent_mode(file_path: str) -> str:
        """Extract agent mode from file path directory structure (not from scenario names)."""
        # Look for agent mode in the directory parts only, excluding filename and scenario names
        dir_parts = [p.lower() for p in Path(file_path).parts[:-1]]  # exclude filename
        
        agent_mode_keywords = ['orchestrator-small-minimal', 'orchestrator-small-balanced', 'orchestrator-small-extensive', 
                               'orchestrator-medium-minimal', 'orchestrator-medium-balanced', 'orchestrator-medium-extensive', 
                               'orchestrator-large-minimal', 'orchestrator-large-balanced', 'orchestrator-large-extensive',
                               'solo', 'pair', 'team', 'company', 'orchestrator', 'test']
        
        for mode in agent_mode_keywords:
            if mode in dir_parts:
                return mode
        return 'unknown'
    
    @staticmethod
    def _find_log_file(data: Dict, file_path: Path) -> Optional[Path]:
        """Find the log file for a given result."""
        scenario_id = data['scenario_id']
        
        # Try the path specified in the JSON first
        log_file = Path(data['log_file_path'])
        if log_file.exists():
            return log_file
        
        # If that doesn't work, try to find it in the scenario directory
        scenario_dir = file_path.parent
        possible_log_files = [
            scenario_dir / "orcagent_run.log",
            scenario_dir / f"{scenario_id}_evaluation_detailed.log",
            scenario_dir / "logs" / "orcagent_run.log",
            scenario_dir / "logs" / "role_repository.log"
        ]
        
        # Also check subdirectories for log files
        for subdir in scenario_dir.rglob("logs"):
            if subdir.is_dir():
                possible_log_files.extend([
                    subdir / "orcagent_run.log",
                    subdir / "role_repository.log"
                ])
        
        for log_file in possible_log_files:
            if log_file.exists():
                return log_file
        
        return None
    
    @staticmethod
    def load_usage_metrics(results_dir: Path) -> pd.DataFrame:
        """
        Extract token, tool, and delegation usage from the log files.
        
        Args:
            results_dir: Path to the results directory
            
        Returns:
            DataFrame containing usage metrics
        """
        if not results_dir.exists():
            raise ValueError(f"Results directory not found: {results_dir}")
        
        logger = get_logger("benchmark:analyzer", "load_usage_metrics")
        logger.info(f"Loading usage metrics from: {results_dir}")
        
        usage_metrics = []
        
        # Look for evaluation results files specifically
        for file_path in results_dir.glob("**/evaluations.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Check if this is a valid evaluation result file
                    required_fields = ['scenario_id', 'model_used', 'log_file_path']
                    
                    if not all(field in data for field in required_fields):
                        logger.warning(f"Skipping {file_path}: missing required fields")
                        continue
                    
                    # Get the associated log file - try multiple possible locations
                    log_file = BenchmarkAnalyzer._find_log_file(data, file_path)
                    if not log_file:
                        logger.warning(f"Log file not found for {data['scenario_id']}")
                        continue
                    
                    # Extract agent mode from path
                    agent_mode = BenchmarkAnalyzer._extract_agent_mode(str(file_path))
                    
                    # Extract metrics from log file
                    metrics = BenchmarkAnalyzer._extract_metrics_from_log(log_file, data, file_path)
                    if metrics:
                        # Store minimal usage metrics for visualizations
                        ordered_metrics = {
                            'scenario_id': metrics['scenario_id'],
                            'agent_mode': agent_mode,
                            'size': metrics['size'],
                            'tokens_used': metrics['tokens_used'],
                            'tool_calls': metrics['tool_calls'],
                            'delegations': metrics['delegations']
                        }
                        usage_metrics.append(ordered_metrics)
                        
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        usage_df = pd.DataFrame(usage_metrics)
        logger.info(f"Loaded usage metrics for {len(usage_df)} scenarios")
        
        return usage_df
    
    @staticmethod
    def _extract_metrics_from_log(log_file: Path, data: Dict, file_path: Path) -> Optional[Dict]:
        """Extract usage metrics from metrics.json files."""
        try:
            # Aggregate metrics across all metrics.json files related to the scenario
            scenario_dir = file_path.parent
            metrics_files = list(scenario_dir.rglob("metrics.json"))

            if not metrics_files:
                logger = get_logger("benchmark:analyzer", "_extract_metrics_from_log")
                logger.warning(f"No metrics.json found for {data['scenario_id']}")
                return None

            total_tokens = 0
            total_tool_calls = 0
            total_delegations = 0

            for metrics_file in metrics_files:
                try:
                    with open(metrics_file, 'r') as f:
                        metrics_data = json.load(f)

                        tokens = metrics_data.get('total_tokens', 0)
                        tools = metrics_data.get('total_tool_calls', 0)

                        # Also count tokens from agent responses
                        agents = metrics_data.get('agents', [])
                        agent_tokens = sum(agent.get('total_tokens', 0) for agent in agents)
                        tokens += agent_tokens

                        # Count delegations from tool functions
                        tool_functions = metrics_data.get('tool_functions', {})
                        delegations = sum(count for func, count in tool_functions.items() if 'delegation' in func.lower())

                        total_tokens += tokens
                        total_tool_calls += tools
                        total_delegations += delegations
                except Exception as inner_exc:
                    logger = get_logger("benchmark:analyzer", "_extract_metrics_from_log")
                    logger.debug(f"Skipping invalid metrics.json at {metrics_file}: {inner_exc}")
                    continue

            size = BenchmarkAnalyzer._extract_scenario_size(str(file_path))

            return {
                'scenario_id': data['scenario_id'],
                'size': size,
                'tokens_used': total_tokens,
                'tool_calls': total_tool_calls,
                'delegations': total_delegations
            }
                
        except Exception as e:
            logger = get_logger("benchmark:analyzer", "_extract_metrics_from_log")
            logger.error(f"Error extracting metrics from {log_file}: {e}")
            return None
    
    @staticmethod
    def get_mean_scores(results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean scores per agent mode across all scenarios.
        
        Args:
            results_df: DataFrame containing benchmark results
        
        Returns:
            DataFrame with mean, std, and count for each agent mode
        """
        return results_df.groupby('agent_mode')['normalized_score'].agg([
            'mean', 'std', 'count'
        ]).round(3)
    
    @staticmethod
    def get_mean_scores_by_size(results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean scores per agent mode and scenario size.
        
        Args:
            results_df: DataFrame containing benchmark results
        
        Returns:
            DataFrame with mean, std, and count for each agent mode and size
        """
        return results_df.groupby(['size', 'agent_mode'])['normalized_score'].agg([
            'mean', 'std', 'count'
        ]).round(3)
    
    @staticmethod
    def get_mean_usage_metrics(usage_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean usage metrics per agent mode.
        
        Args:
            usage_df: DataFrame containing usage metrics
        
        Returns:
            DataFrame with mean and std for tokens, tools, and delegations
        """
        return usage_df.groupby('agent_mode')[['tokens_used', 'tool_calls', 'delegations']].agg([
            'mean', 'std'
        ]).round(2)
    
    @staticmethod
    def get_mean_usage_metrics_by_size(usage_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean usage metrics per agent mode and scenario size.
        
        Args:
            usage_df: DataFrame containing usage metrics
        
        Returns:
            DataFrame with mean and std for tokens, tools, and delegations by size
        """
        return usage_df.groupby(['size', 'agent_mode'])[
            ['tokens_used', 'tool_calls', 'delegations']
        ].agg(['mean', 'std']).round(2)
    
    @staticmethod
    def _read_roles_count_from_logs(scenario_dir: Path) -> int:
        """Read the number of roles from role_repository.log files under a scenario directory.

        Strategy: search recursively for role_repository.log; for each file, parse JSON and
        determine number of roles via len(data['roles']) if present, otherwise use
        data['summary']['total_roles'] if available. Return the maximum count found.
        """
        max_roles = 0
        try:
            for log_path in scenario_dir.rglob("role_repository.log"):
                try:
                    with open(log_path, "r") as fh:
                        data = json.load(fh)
                        roles_obj = data.get("roles")
                        if isinstance(roles_obj, dict):
                            count = len(roles_obj.keys())
                        else:
                            summary = data.get("summary", {})
                            count = int(summary.get("total_roles", 0))
                        if count > max_roles:
                            max_roles = count
                except Exception as inner_exc:
                    logger = get_logger("benchmark:analyzer", "_read_roles_count_from_logs")
                    logger.debug(f"Skipping invalid role_repository.log at {log_path}: {inner_exc}")
                    continue
        except Exception as exc:
            logger = get_logger("benchmark:analyzer", "_read_roles_count_from_logs")
            logger.error(f"Error scanning for role_repository.log in {scenario_dir}: {exc}")
            return 0

        return max_roles

    @staticmethod
    def get_mean_roles_by_size(results_dir: Path) -> pd.DataFrame:
        """Compute mean number of roles per scenario complexity (size) grouped by orchestrator modes.

        Args:
            results_dir: Root directory containing benchmarking results
            agent_mode_filter: If provided, only include scenarios for this agent mode

        Returns:
            DataFrame indexed by size with orchestrator modes as columns, containing mean roles
        """
        if not results_dir.exists():
            raise ValueError(f"Results directory not found: {results_dir}")

        rows: List[Dict[str, object]] = []
        logger = get_logger("benchmark:analyzer", "get_mean_roles_by_size")
        
        for eval_file in results_dir.glob("**/evaluations.json"):
            try:
                size = BenchmarkAnalyzer._extract_scenario_size(str(eval_file))
                mode = BenchmarkAnalyzer._extract_agent_mode(str(eval_file))
                
                # Filter for orchestrator modes only
                if not mode.startswith('orchestrator'):
                    continue
                
                scenario_dir = eval_file.parent
                roles_count = BenchmarkAnalyzer._read_roles_count_from_logs(scenario_dir)
                rows.append({'size': size, 'agent_mode': mode, 'roles_count': roles_count})
            except Exception as exc:
                logger.error(f"Error processing {eval_file}: {exc}")
                continue

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=['mean_roles'])

        # Group by size and agent_mode, then pivot to get orchestrator modes as columns
        grouped = df.groupby(['size', 'agent_mode'])['roles_count'].mean().round(2)
        pivoted = grouped.unstack(fill_value=0)

        # Ensure logical ordering of scenario complexities
        complexity_order = ['test', 'small', 'medium', 'large', 'enterprise']
        available = [c for c in complexity_order if c in pivoted.index]
        if available:
            pivoted = pivoted.reindex(available)

        return pivoted

    @staticmethod
    def get_grouped_bar_chart_data(usage_df: pd.DataFrame, metric: str) -> pd.DataFrame:
        """
        Prepare data for grouped bar charts with agent modes grouped by scenario complexity.
        
        Args:
            usage_df: DataFrame containing usage metrics
            metric: The metric to analyze ('tokens_used', 'tool_calls', or 'delegations')
            
        Returns:
            DataFrame with complexity as index and agent modes as columns, containing mean values
        """
        if metric not in ['tokens_used', 'tool_calls', 'delegations']:
            raise ValueError("Metric must be one of: tokens_used, tool_calls, delegations")
        
        # Group by size (complexity) and agent_mode, calculate mean
        grouped_data = usage_df.groupby(['size', 'agent_mode'])[metric].mean().unstack(fill_value=0)
        
        # Sort complexities in logical order
        complexity_order = ['test', 'small', 'medium', 'large', 'enterprise']
        available_complexities = [c for c in complexity_order if c in grouped_data.index]
        
        if available_complexities:
            grouped_data = grouped_data.reindex(available_complexities)
        
        return grouped_data.round(2)
    
    @staticmethod
    def get_roles_bar_chart_data(results_dir: Path) -> pd.DataFrame:
        """Get data formatted for bar chart visualization with separate bars for each orchestrator mode.
        
        Args:
            results_dir: Root directory containing benchmarking results
            
        Returns:
            DataFrame with orchestrator modes as index and sizes as columns, suitable for bar chart plotting
        """
        # Get the pivoted data from get_mean_roles_by_size
        roles_data = BenchmarkAnalyzer.get_mean_roles_by_size(results_dir)
        
        if roles_data.empty:
            return pd.DataFrame()
        
        # Transpose to get orchestrator modes as index (x-axis) and sizes as columns (separate bars)
        # This will create separate bars for each orchestrator mode
        bar_chart_data = roles_data.T
        
        return bar_chart_data
    
    @staticmethod
    def get_summary_statistics(results_df: pd.DataFrame, usage_df: Optional[pd.DataFrame] = None) -> Dict:
        """
        Get comprehensive summary statistics.
        
        Args:
            results_df: DataFrame containing benchmark results
            usage_df: Optional DataFrame containing usage metrics
        
        Returns:
            Dictionary containing various summary statistics
        """
        summary = {
            'total_scenarios': len(results_df),
            'unique_agent_modes': results_df['agent_mode'].nunique(),
            'unique_sizes': results_df['size'].nunique(),
            'overall_mean_score': results_df['normalized_score'].mean(),
            'overall_std_score': results_df['normalized_score'].std(),
            'mean_scores_by_agent_mode': BenchmarkAnalyzer.get_mean_scores(results_df).to_dict(),
            'mean_scores_by_size': BenchmarkAnalyzer.get_mean_scores_by_size(results_df).to_dict()
        }
        
        if usage_df is not None:
            summary.update({
                'scenarios_with_usage_data': len(usage_df),
                'mean_usage_by_agent_mode': BenchmarkAnalyzer.get_mean_usage_metrics(usage_df).to_dict(),
                'mean_usage_by_size': BenchmarkAnalyzer.get_mean_usage_metrics_by_size(usage_df).to_dict()
            })
        
        return summary 
    
    @staticmethod
    def generate_all_data_files(results_dir: Path, output_dir: Path) -> None:
        """
        Generate all data files for visualizations.
        
        Args:
            results_dir: Path to the results directory
            output_dir: Path to the directory where data files will be saved
        """
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger = get_logger("benchmark:analyzer", "generate_all_data_files")
        logger.info(f"Generating data files from {results_dir} to {output_dir}")
        
        # Load data
        results_df = BenchmarkAnalyzer.load_results(results_dir)
        usage_df = BenchmarkAnalyzer.load_usage_metrics(results_dir)
        
        # Generate only essential data files for remaining visualizations
        BenchmarkAnalyzer._save_minimal_benchmark_results(results_df, output_dir)
        BenchmarkAnalyzer._save_minimal_usage_metrics(usage_df, output_dir)
        BenchmarkAnalyzer._save_roles_data(results_dir, output_dir)
        
        logger.info("All data files generated successfully")
    
    @staticmethod
    def _save_minimal_benchmark_results(results_df: pd.DataFrame, output_dir: Path) -> None:
        """Save minimal benchmark results to CSV for visualization."""
        results_df.to_csv(output_dir / "benchmark_results.csv", index=False)
    
    @staticmethod
    def _save_minimal_usage_metrics(usage_df: pd.DataFrame, output_dir: Path) -> None:
        """Save pre-aggregated usage metrics (mean values only) since error bars were removed."""
        # Aggregate to mean values by agent_mode (no error bars means no need for individual data points)
        aggregated_usage = usage_df.groupby('agent_mode')[['tokens_used', 'tool_calls']].mean().reset_index()
        aggregated_usage.to_csv(output_dir / "usage_metrics.csv", index=False)
    
    @staticmethod
    def _save_roles_data(results_dir: Path, output_dir: Path) -> None:
        """Save only the roles bar chart data that's actually used."""
        try:
            # Only save bar chart formatted data (the only one used in notebook)
            bar_chart_data = BenchmarkAnalyzer.get_roles_bar_chart_data(results_dir)
            if not bar_chart_data.empty:
                bar_chart_data.to_csv(output_dir / "roles_bar_chart_data.csv")
            else:
                # Create empty file to indicate no orchestrator results
                (output_dir / "no_orchestrator_results.txt").touch()
        except Exception:
            # Create empty file to indicate no orchestrator results
            (output_dir / "no_orchestrator_results.txt").touch()
    
