#!/usr/bin/env python3
"""
Benchmark Runner Module

Orchestrates the execution of benchmark scenarios and manages
the overall benchmark process with comprehensive reporting.
"""

import os
import sys
import time
import json
import shutil
import subprocess
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import asdict
import re
from dotenv import load_dotenv

from benchmarking.benchmark_scenarios import BenchmarkScenario, get_scenario_by_id, create_benchmark_scenarios, ScenarioComplexity
from benchmarking.benchmark_evaluator import BenchmarkEvaluator, ScenarioEvaluationResult, EvaluationResult
from logger.log_wrapper import get_logger
from benchmarking.evaluations.gh_actions_wait_utils import wait_for_active_workflows

load_dotenv(override=True)

# Constants
SCENARIO_EXECUTION_TIMEOUT = 3600 * 24  # 24 hour timeout for scenario execution


class BenchmarkRunner:
    """Main benchmark runner that orchestrates scenario execution and evaluation."""
    
    def __init__(self, output_dir: str = "benchmarking/results"):
        self.logger = get_logger("benchmark:runner", __name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        
        # Check if output_dir already contains a timestamp (YYYYMMDD_HHMMSS format)
        timestamp_pattern = r'\d{8}_\d{6}'
        if re.search(timestamp_pattern, str(self.output_dir)):
            # Output dir already contains timestamp, use it as the benchmark run dir
            self.benchmark_run_dir = self.output_dir
            # Extract timestamp from the path
            match = re.search(timestamp_pattern, str(self.output_dir))
            self.benchmark_timestamp = match.group() if match else datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Extract agent name from the path
            path_parts = self.output_dir.parts
            if len(path_parts) >= 2:
                # The agent name should be the last part of the path
                self.agent_name = path_parts[-1]
            else:
                self.agent_name = "unknown"
        else:
            # Create benchmark run timestamp directory
            self.benchmark_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.benchmark_run_dir = self.output_dir / self.benchmark_timestamp
            self.benchmark_run_dir.mkdir(exist_ok=True)
            
            # Extract agent name from output_dir path - handle nested paths
            if self.output_dir.name != "results":
                self.agent_name = self.output_dir.name
            else:
                # If we're in the results directory, use a default name
                self.agent_name = "unknown"
        
        self.agent_dir = self.benchmark_run_dir
        self.agent_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Initialized benchmark runner with run directory: {self.benchmark_run_dir}")
        self.logger.info(f"Agent directory: {self.agent_dir}")
    

    
    def _get_evaluation_files_for_scenario(self, scenario_id: str) -> List[str]:
        """Get evaluation files for a scenario."""
        from benchmarking.benchmark_scenarios import _scenario_complexity_from_id
        
        scenario_dir = Path("benchmarking/scenarios")
        evaluation_files = []
        
        try:
            # Dynamically determine the complexity level for this scenario
            complexity = _scenario_complexity_from_id(scenario_id)
            complexity_dir = scenario_dir / complexity.value
            
            # Check for initial evaluations
            initial_eval1 = complexity_dir / f"{scenario_id}_initial_evaluation1.json"
            initial_eval2 = complexity_dir / f"{scenario_id}_initial_evaluation2.json"
            
            if initial_eval1.exists():
                evaluation_files.append(str(initial_eval1))
            if initial_eval2.exists():
                evaluation_files.append(str(initial_eval2))
            
            # Check for followup evaluations
            followup_eval1 = complexity_dir / f"{scenario_id}_followup_evaluation1.json"
            followup_eval2 = complexity_dir / f"{scenario_id}_followup_evaluation2.json"
            
            if followup_eval1.exists():
                evaluation_files.append(str(followup_eval1))
            if followup_eval2.exists():
                evaluation_files.append(str(followup_eval2))
            
        except (ValueError, FileNotFoundError):
            # If we can't determine complexity or no files found, return empty list
            # This assumes all scenarios have been migrated to the new evaluation approach
            self.logger.warning(f"Could not find evaluation files for scenario {scenario_id}")
        
        return evaluation_files
    
    def _extract_website_url_from_log(self, log_file_path: str) -> Optional[str]:
        """Extract website URL using the same approach as screenshot functionality."""
        try:
            # Use the same AWS CLI approach as screenshot functionality
            from benchmarking.evaluations.aws_cli_utils import get_prod_load_balancer_url
            url = get_prod_load_balancer_url()
            
            if url and not url.startswith("Error"):
                self.logger.info(f"Extracted website URL from AWS CLI: {url}")
                return url
            else:
                self.logger.warning(f"Could not get website URL from AWS CLI: {url}")
                return None
                
        except Exception as e:
            self.logger.warning(f"Could not extract website URL: {e}")
            return None
    
    def run_single_scenario(self, scenario_id: str, agents_mode: str, model: str = "gpt-5") -> ScenarioEvaluationResult:
        """
        Run a single benchmark scenario.
        
        Args:
            scenario_id: ID of the scenario to run
            agents_mode: Agent mode to use
            model: LLM model to use (defaults to 'gpt-5')
            
        Returns:
            ScenarioEvaluationResult with evaluation results
        """
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")
        
        print(f"\nRunning scenario: {scenario.id}")
        self.logger.info(f"Starting execution of scenario: {scenario.id}")
        
        # Run initial prompt (always clean for initial prompt)
        initial_result = self._execute_scenario_prompt(
            scenario.initial_prompt, 
            f"{scenario_id}_initial",
            True,  # Always clean for initial prompt
            agents_mode,
            model
        )
        
        if not initial_result['success']:
            self.logger.error(f"Initial prompt failed for {scenario.id}")
            return self._create_failed_result(scenario, initial_result['log_file'], 0, model)
        
        # Run follow-up prompt (never clean for follow-up)
        follow_up_result = self._execute_scenario_prompt(
            scenario.follow_up_prompt,
            f"{scenario_id}_followup", 
            False,  # Never clean for follow-up
            agents_mode,
            model
        )
        
        if not follow_up_result['success']:
            self.logger.warning(f"Follow-up prompt failed for {scenario.id}")
            # Still evaluate initial results
        
        # Calculate total execution time
        total_time = self._calculate_execution_time(initial_result['log_file'])
        if follow_up_result['success']:
            total_time += self._calculate_execution_time(follow_up_result['log_file'])
        
        # Get evaluation files for this scenario
        evaluation_files = self._get_evaluation_files_for_scenario(scenario_id)
        
        print(f"\nEvaluating scenario: {scenario.id}")
        self.logger.info(f"Starting evaluation of scenario: {scenario.id}")

        # Ensure any active GitHub Actions in the repo have completed to avoid race conditions
        try:
            wait_message = wait_for_active_workflows(timeout_seconds=600, poll_interval_seconds=5)
            self.logger.info(f"GitHub Actions wait status: {wait_message}")
        except Exception as e:
            self.logger.warning(f"Could not wait for GitHub Actions workflows: {e}")
        
        # Create scenario directory for evaluations.json
        scenario_dir = self.agent_dir / scenario.id
        scenario_dir.mkdir(exist_ok=True)
        
        # Evaluate results using AI-driven evaluator with proper context manager
        evaluator: BenchmarkEvaluator
        with BenchmarkEvaluator() as evaluator:
            # Provide a non-optional website URL string to satisfy typing
            website_url = self._extract_website_url_from_log(initial_result['log_file']) or ""
            evaluation_result = evaluator.evaluate_scenario(
                scenario.id,
                scenario.id,
                evaluation_files,
                initial_result['log_file'], # Use initial_result['log_file'] for evaluation
                total_time,
                model,
                website_url, # Use initial_result['log_file'] for website URL
                scenario_dir
            )
        
        # Save individual scenario report
        self._save_scenario_report(evaluation_result)
        
        # Move run folders to scenario directory - pass both initial and follow-up results
        self._move_run_folders_to_scenario(evaluation_result, initial_result, follow_up_result)
        
        # Run evaluation utilities
        self._run_evaluation_utilities(evaluation_result)
        
        return evaluation_result
    
    def run_all_scenarios(self, agents_mode: str, model: str = "gpt-5") -> List[ScenarioEvaluationResult]:
        """
        Run all benchmark scenarios (excluding test complexity).
        
        Args:
            agents_mode: Agent mode to use
            model: LLM model to use (defaults to 'gpt-5')
            
        Returns:
            List of ScenarioEvaluationResult objects
        """
        scenarios = create_benchmark_scenarios()
        # Filter out test complexity scenarios when running all scenarios
        scenarios = [s for s in scenarios if s.complexity != ScenarioComplexity.TEST]
        results = []
        
        self.logger.info(f"Starting benchmark run with {len(scenarios)} scenarios (excluding test complexity)")
        
        for i, scenario in enumerate(scenarios, 1):
            self.logger.info(f"Running scenario {i}/{len(scenarios)}: {scenario.id}")
            
            try:
                result = self.run_single_scenario(scenario.id, agents_mode, model)
                results.append(result)
                
                # Update summary after each scenario
                self._update_summary_report(results)
                
            except Exception as e:
                self.logger.error(f"Failed to run scenario {scenario.id}: {e}")
                # Create failed result
                failed_result = self._create_failed_result(scenario, "", 0, model)
                results.append(failed_result)
        
        # Generate final summary
        self._generate_final_summary(results)
        
        return results
    
    def run_scenarios_by_complexity(self, complexity: str, agents_mode: str, model: str = "gpt-5") -> List[ScenarioEvaluationResult]:
        """
        Run scenarios of a specific complexity level.
        
        Args:
            complexity: Complexity level to run
            agents_mode: Agent mode to use
            model: LLM model to use (defaults to 'gpt-5')
            
        Returns:
            List of ScenarioEvaluationResult objects
        """
        try:
            complexity_enum = ScenarioComplexity(complexity.lower())
        except ValueError:
            raise ValueError(f"Invalid complexity level: {complexity}")
        
        scenarios = [s for s in create_benchmark_scenarios() if s.complexity == complexity_enum]
        
        if not scenarios:
            raise ValueError(f"No scenarios found for complexity level: {complexity}")
        
        self.logger.info(f"Running {len(scenarios)} scenarios with complexity: {complexity}")
        
        results = []
        for scenario in scenarios:
            try:
                result = self.run_single_scenario(scenario.id, agents_mode, model)
                results.append(result)
                self._update_summary_report(results)
            except Exception as e:
                self.logger.error(f"Failed to run scenario {scenario.id}: {e}")
                self.logger.error(f"Stack trace for scenario {scenario.id}: {traceback.format_exc()}")
                # Create failed result
                failed_result = self._create_failed_result(scenario, "", 0, model)
                results.append(failed_result)
        
        if not results:
            raise ValueError(f"No scenarios were executed successfully for complexity level: {complexity}")
        
        self._generate_final_summary(results)
        return results
    
    def _execute_scenario_prompt(self, prompt: str, scenario_id: str, 
                                clean_env: bool, agents_mode: str, model: str) -> Dict[str, Any]:
        """Execute a scenario prompt using main.py."""
        try:
            # Build command
            cmd = [
                sys.executable, "main.py",
                "--prompt", prompt,
                "--agents", agents_mode,
                "--model", model
            ]
            
            if clean_env:
                cmd.append("--clean")
            
            self.logger.info(f"Executing command: {' '.join(cmd)}")
            
            # Execute main.py
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=SCENARIO_EXECUTION_TIMEOUT,
                cwd=os.getcwd()  # Explicitly set working directory
            )
            execution_time = time.time() - start_time
            
            # Parse log file path from output
            log_file = None
            for line in result.stdout.split('\n'):
                if "Results logged to:" in line:
                    log_file = line.split("Results logged to:")[-1].strip()
                    self.logger.info(f"Found log file in stdout: {log_file}")
                    break
            
            if not log_file:
                # Try to find log file in stderr
                for line in result.stderr.split('\n'):
                    if "Results logged to:" in line:
                        log_file = line.split("Results logged to:")[-1].strip()
                        self.logger.info(f"Found log file in stderr: {log_file}")
                        break
            
            if not log_file:
                self.logger.warning(f"Could not find log file path in output for {scenario_id}")
                self.logger.debug(f"stdout: {result.stdout}")
                self.logger.debug(f"stderr: {result.stderr}")
            
            success = result.returncode == 0
            
            return {
                'success': success,
                'log_file': log_file,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'execution_time': execution_time
            }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Scenario execution timed out: {scenario_id}")
            self.logger.error(f"Stack trace for timeout in scenario {scenario_id}: {traceback.format_exc()}")
            return {
                'success': False,
                'log_file': None,
                'stdout': '',
                'stderr': 'Execution timed out',
                'returncode': -1,
                'execution_time': SCENARIO_EXECUTION_TIMEOUT
            }
        except Exception as e:
            self.logger.error(f"Error executing scenario {scenario_id}: {e}")
            self.logger.error(f"Stack trace for scenario {scenario_id}: {traceback.format_exc()}")
            return {
                'success': False,
                'log_file': None,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'execution_time': 0
            }
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if not timestamp_str or timestamp_str.strip() == "":
            return None
            
        timestamp_str = timestamp_str.strip()
        
        # Try ISO format first
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            pass
            
        # Try log format: "2025-08-07 08:27:31,674"
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            pass
            
        # Try standard format: "2025-08-07 08:27:31"
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
            
        return None

    def _calculate_execution_time(self, log_file_path: str) -> float:
        """Calculate execution time from log file."""
        if not log_file_path or not os.path.exists(log_file_path):
            return 0.0
        
        try:
            # Look for timestamps in log file
            with open(log_file_path, 'r') as f:
                content = f.read()
            
            # Extract timestamps and calculate duration
            lines = content.split('\n')
            start_time = None
            end_time = None
            
            for line in lines:
                # Look for WORKFLOW EXECUTION STARTED
                if "WORKFLOW EXECUTION STARTED" in line:
                    try:
                        # Extract timestamp from the log line itself
                        # Format: "2025-08-07 08:27:31,674 - __main__ - INFO - WORKFLOW EXECUTION STARTED - ..."
                        timestamp_str = line.split(" - ")[0].strip()
                        start_time = self._parse_timestamp(timestamp_str)
                    except (ValueError, IndexError):
                        self.logger.warning(f"Could not parse start timestamp from line: {line}")
                        pass
                # Look for WORKFLOW EXECUTION COMPLETED
                elif "WORKFLOW EXECUTION COMPLETED" in line:
                    try:
                        # Check if the line has "Timestamp: " format
                        if "Timestamp: " in line:
                            # Format: "2025-08-07 08:37:40,161 - __main__ - INFO - WORKFLOW EXECUTION COMPLETED - Timestamp: 2025-08-07T08:37:40.161717"
                            timestamp_str = line.split("Timestamp: ")[-1].strip()
                            end_time = self._parse_timestamp(timestamp_str)
                        else:
                            # Extract timestamp from the log line itself
                            # Format: "2025-08-07 08:32:11,923 - __main__ - INFO - WORKFLOW EXECUTION COMPLETED - ..."
                            timestamp_str = line.split(" - ")[0].strip()
                            end_time = self._parse_timestamp(timestamp_str)
                    except (ValueError, IndexError):
                        self.logger.warning(f"Could not parse end timestamp from line: {line}")
                        pass
                # Fallback: Look for timestamp at end of prompt section
                elif "Timestamp:" in line and start_time is None:
                    try:
                        # Extract timestamp from lines like "- Timestamp: 2025-08-07T08:27:31.674115"
                        if line.strip().endswith("Timestamp:"):
                            # Look at next line for the actual timestamp
                            continue
                        timestamp_str = line.split("Timestamp: ")[-1].strip()
                        if timestamp_str and timestamp_str != "":
                            start_time = self._parse_timestamp(timestamp_str)
                    except (ValueError, IndexError):
                        pass
                # Fallback: Look for "Active group chat contains" as start indicator
                elif "Active group chat contains" in line and start_time is None:
                    # Extract timestamp from the log line itself
                    try:
                        # Parse timestamp from log line format: "2025-08-07 08:27:31,674 - __main__ - INFO - ..."
                        timestamp_str = line.split(" - ")[0].strip()
                        start_time = self._parse_timestamp(timestamp_str)
                    except (ValueError, IndexError):
                        pass
            
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds() / 60.0  # Convert to minutes
                return duration
            else:
                self.logger.warning(f"Missing {'start' if not start_time else 'end'} timestamp in log file")
                return 0.0
            
        except Exception as e:
            self.logger.warning(f"Could not calculate execution time: {e}")
            return 0.0
    
    def _create_failed_result(self, scenario: BenchmarkScenario, log_file: str, 
                             execution_time: float, model: str) -> ScenarioEvaluationResult:
        """Create a failed result when scenario execution fails."""
        failed_evaluations = []
        
        # Create failed results for all evaluations (initial + followup)
        all_evaluations = scenario.initial_evaluations + scenario.followup_evaluations
        
        for evaluation in all_evaluations:
            failed_evaluations.append(EvaluationResult(
                evaluation_name=evaluation.name,
                passed=False,
                score=0.0,
                details='Scenario execution failed',
                steps_completed=0,
                total_steps=len(evaluation.steps),
                error_message='Scenario execution failed'
            ))
        
        return ScenarioEvaluationResult(
            scenario_id=scenario.id,
            scenario_name=scenario.id,
            total_score=0.0,
            max_possible_score=sum(eval.score for eval in failed_evaluations),
            passed_evaluations=0,
            total_evaluations=len(failed_evaluations),
            evaluation_results=failed_evaluations,
            execution_time_minutes=execution_time,
            log_file_path=log_file,
            model_used=model
        )
    
    def _save_scenario_report(self, result: ScenarioEvaluationResult) -> None:
        """Save individual scenario report."""
        # Create scenario directory
        scenario_dir = self.agent_dir / result.scenario_id
        scenario_dir.mkdir(exist_ok=True)
        
        # Save as evaluations.json in scenario directory
        evaluations_file = scenario_dir / "evaluations.json"
        
        # Convert result to dict for JSON serialization
        result_dict = asdict(result)
        
        with open(evaluations_file, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        self.logger.info(f"Saved scenario evaluations: {evaluations_file}")
    
    def _move_run_folders_to_scenario(self, result: ScenarioEvaluationResult, 
                                     initial_result: Dict[str, Any], 
                                     follow_up_result: Dict[str, Any]) -> None:
        """Move OrcAgent_runs folders to scenario directory."""
        try:
            # Scenario directory should already exist from _save_scenario_report
            scenario_dir = self.agent_dir / result.scenario_id
            
            # Move initial run folder
            if initial_result.get('log_file'):
                self._move_single_run_folder(scenario_dir, initial_result['log_file'], "initial")
            
            # Move follow-up run folder
            if follow_up_result.get('log_file'):
                self._move_single_run_folder(scenario_dir, follow_up_result['log_file'], "followup")
                
        except Exception as e:
            self.logger.error(f"Error moving run folders: {e}")
    
    def _move_single_run_folder(self, scenario_dir: Path, log_file_path: str, run_type: str) -> None:
        """Move a single run folder to the scenario directory."""
        try:
            self.logger.info(f"Attempting to move {run_type} run folder from log file: {log_file_path}")
            log_file_path_obj = Path(log_file_path)
            if log_file_path_obj.exists():
                # Extract timestamp from path like "../OrcAgent_runs/20250723-034725/logs/orcagent_run.log"
                path_parts = log_file_path_obj.parts
                self.logger.debug(f"Log file path parts: {path_parts}")
                
                if len(path_parts) >= 3 and "OrcAgent_runs" in path_parts:
                    run_timestamp = path_parts[path_parts.index("OrcAgent_runs") + 1]
                    source_run_dir = Path(f"../OrcAgent_runs/{run_timestamp}")
                    
                    self.logger.info(f"Extracted timestamp: {run_timestamp}")
                    self.logger.info(f"Source run directory: {source_run_dir}")
                    
                    if source_run_dir.exists():
                        # Move the entire run directory to scenario folder with type suffix
                        target_run_dir = scenario_dir / f"{run_timestamp}_{run_type}"
                        self.logger.info(f"Target run directory: {target_run_dir}")
                        
                        if not target_run_dir.exists():
                            shutil.move(str(source_run_dir), str(target_run_dir))
                            self.logger.info(f"Moved {run_type} run folder {source_run_dir} to {target_run_dir}")
                        else:
                            self.logger.warning(f"Target {run_type} run directory already exists: {target_run_dir}")
                    else:
                        self.logger.warning(f"Source {run_type} run directory not found: {source_run_dir}")
                else:
                    self.logger.warning(f"Could not extract timestamp from {run_type} log file path: {log_file_path}")
                    self.logger.debug(f"Path parts: {path_parts}")
            else:
                self.logger.warning(f"{run_type.capitalize()} log file not found: {log_file_path}")
                
        except Exception as e:
            self.logger.error(f"Error moving {run_type} run folder: {e}")
    
    def _run_evaluation_utilities(self, result: ScenarioEvaluationResult) -> None:
        """Run evaluation utilities after scenario completion."""
        try:
            # Create scenario directory if it doesn't exist
            scenario_dir = self.agent_dir / result.scenario_id
            scenario_dir.mkdir(exist_ok=True)
            
            self.logger.info(f"Running evaluation utilities for scenario: {result.scenario_id}")
            
            # Take screenshot of prod ELB root page
            try:
                from benchmarking.evaluations.playwright_utils import take_prod_screenshot
                screenshot_path = scenario_dir / "prod_screenshot.png"
                screenshot_result = take_prod_screenshot(str(screenshot_path))
                if screenshot_result.startswith("Error"):
                    self.logger.error(f"Prod screenshot failed: {screenshot_result}")
                else:
                    self.logger.info(f"Prod screenshot: {screenshot_result}")
            except Exception as e:
                self.logger.error(f"Failed to take prod screenshot: {e}")
            
            # Dump Notion root page
            try:
                from benchmarking.evaluations.notion_utils import dump_notion_root_page
                notion_dump_path = scenario_dir / "notion_dump.json"
                notion_result = dump_notion_root_page(str(notion_dump_path))
                if notion_result.startswith("Error") or notion_result.startswith("Failed"):
                    self.logger.error(f"Notion dump failed: {notion_result}")
                else:
                    self.logger.info(f"Notion dump: {notion_result}")
            except Exception as e:
                self.logger.error(f"Failed to dump Notion page: {e}")
            
            # Get AWS service health
            try:
                from benchmarking.evaluations.aws_cli_utils import get_prod_service_health
                health_result = get_prod_service_health()
                health_path = scenario_dir / "aws_health.txt"
                with open(health_path, 'w') as f:
                    f.write(health_result)
                if health_result.startswith("Error"):
                    self.logger.error(f"AWS health check failed: {health_result}")
                else:
                    self.logger.info(f"AWS health check completed")
            except Exception as e:
                self.logger.error(f"Failed to get AWS health: {e}")
                
        except Exception as e:
            self.logger.error(f"Error running evaluation utilities: {e}")
    
    def _update_summary_report(self, results: List[ScenarioEvaluationResult]) -> None:
        """Update ongoing summary report."""
        summary = self._generate_summary_data(results)
        
        summary_file = self.agent_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Also save timestamped version
        timestamped_file = self.agent_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(timestamped_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
    
    def _generate_final_summary(self, results: List[ScenarioEvaluationResult]) -> None:
        """Generate final comprehensive summary."""
        summary = self._generate_summary_data(results)
        
        # Add final summary statistics
        summary['final_summary'] = {
            'total_scenarios': len(results),
            'successful_scenarios': len([r for r in results if r.passed_evaluations == r.total_evaluations]),
            'failed_scenarios': len([r for r in results if r.passed_evaluations != r.total_evaluations]),
            'average_score': sum(r.total_score for r in results) / len(results) if results else 0,
            'average_execution_time': sum(r.execution_time_minutes for r in results) / len(results) if results else 0,
            'completion_timestamp': datetime.now().isoformat()
        }
        
        final_summary_file = self.agent_dir / f"final_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(final_summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Generate human-readable summary
        self._generate_human_readable_summary(summary, final_summary_file.with_suffix('.txt'))
        
        self.logger.info(f"Generated final summary: {final_summary_file}")
    
    def _generate_summary_data(self, results: List[ScenarioEvaluationResult]) -> Dict[str, Any]:
        """Generate summary data from results."""
        # Get unique models used
        models_used = list(set(result.model_used for result in results))
        
        summary: Dict[str, Any] = {
            'benchmark_run_id': self.benchmark_timestamp,
            'agent_name': self.agent_name,
            'models_used': models_used,
            'scenarios': [],
            'statistics': {
                'total_scenarios': len(results),
                'successful_scenarios': 0,
                'failed_scenarios': 0,
                'total_score': 0,
                'max_possible_score': 0,
                'average_score': 0,
                'total_execution_time': 0,
                'average_execution_time': 0
            },
            'complexity_breakdown': {
                'small': {'count': 0, 'successful': 0, 'average_score': 0},
                'medium': {'count': 0, 'successful': 0, 'average_score': 0},
                'large': {'count': 0, 'successful': 0, 'average_score': 0},
                'enterprise': {'count': 0, 'successful': 0, 'average_score': 0},
                'test': {'count': 0, 'successful': 0, 'average_score': 0}
            }
        }
        
        for result in results:
            # Add scenario result
            scenario_data = asdict(result)
            summary['scenarios'].append(scenario_data)
            
            # Update statistics
            if result.passed_evaluations == result.total_evaluations:
                summary['statistics']['successful_scenarios'] += 1
            else:
                summary['statistics']['failed_scenarios'] += 1
            
            summary['statistics']['total_score'] += result.total_score
            summary['statistics']['max_possible_score'] += result.max_possible_score
            summary['statistics']['total_execution_time'] += result.execution_time_minutes
        
        # Calculate averages
        if results:
            summary['statistics']['average_score'] = summary['statistics']['total_score'] / len(results)
            summary['statistics']['average_execution_time'] = summary['statistics']['total_execution_time'] / len(results)
        
        # Complexity breakdown
        for result in results:
            scenario = get_scenario_by_id(result.scenario_id)
            if scenario:
                complexity = scenario.complexity.value
                summary['complexity_breakdown'][complexity]['count'] += 1
                if result.passed_evaluations == result.total_evaluations:
                    summary['complexity_breakdown'][complexity]['successful'] += 1
                
                # Calculate average score for this complexity
                complexity_results = []
                for r in results:
                    r_scenario = get_scenario_by_id(r.scenario_id)
                    if r_scenario and r_scenario.complexity.value == complexity:
                        complexity_results.append(r)
                if complexity_results:
                    avg_score = sum(r.total_score for r in complexity_results) / len(complexity_results)
                    summary['complexity_breakdown'][complexity]['average_score'] = avg_score
        
        return summary
    
    def _generate_human_readable_summary(self, summary: Dict[str, Any], output_file: Path) -> None:
        """Generate human-readable summary report."""
        with open(output_file, 'w') as f:
            f.write("BENCHMARK EXECUTION SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Benchmark Run ID: {summary['benchmark_run_id']}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Overall statistics
            stats = summary['statistics']
            f.write("OVERALL STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Scenarios: {stats['total_scenarios']}\n")
            f.write(f"Successful: {stats['successful_scenarios']}\n")
            f.write(f"Failed: {stats['failed_scenarios']}\n")
            f.write(f"Success Rate: {(stats['successful_scenarios']/stats['total_scenarios']*100):.1f}%\n")
            f.write(f"Average Score: {stats['average_score']:.2f}/{stats['max_possible_score']:.2f}\n")
            f.write(f"Average Execution Time: {stats['average_execution_time']:.1f} minutes\n\n")
            
            # Complexity breakdown
            f.write("COMPLEXITY BREAKDOWN\n")
            f.write("-" * 20 + "\n")
            for complexity, data in summary['complexity_breakdown'].items():
                if data['count'] > 0:
                    success_rate = (data['successful'] / data['count'] * 100) if data['count'] > 0 else 0
                    f.write(f"{complexity.title()}:\n")
                    f.write(f"  Count: {data['count']}\n")
                    f.write(f"  Successful: {data['successful']}\n")
                    f.write(f"  Success Rate: {success_rate:.1f}%\n")
                    f.write(f"  Average Score: {data['average_score']:.2f}\n\n")
            
            # Individual scenario results
            f.write("INDIVIDUAL SCENARIO RESULTS\n")
            f.write("-" * 30 + "\n")
            for scenario in summary['scenarios']:
                status = "PASS" if scenario['passed_evaluations'] == scenario['total_evaluations'] else "FAIL"
                f.write(f"{scenario['scenario_name']} ({scenario['scenario_id']}): {status}\n")
                f.write(f"  Score: {scenario['total_score']:.2f}/{scenario['max_possible_score']:.2f}\n")
                f.write(f"  Execution Time: {scenario['execution_time_minutes']:.1f} minutes\n")
                f.write(f"  Passed Evaluations: {scenario['passed_evaluations']}/{scenario['total_evaluations']}\n\n")
        
        self.logger.info(f"Generated human-readable summary: {output_file}")
    
    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """Get list of available scenarios with details."""
        scenarios = create_benchmark_scenarios()
        return [
            {
                'id': s.id,
                'complexity': s.complexity.value,
                'initial_evaluations_count': len(s.initial_evaluations),
                'followup_evaluations_count': len(s.followup_evaluations)
            }
            for s in scenarios
        ]
    
    def get_scenario_details(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific scenario."""
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            return None
        
        return {
            'id': scenario.id,
            'complexity': scenario.complexity.value,
            'initial_prompt': scenario.initial_prompt,
            'follow_up_prompt': scenario.follow_up_prompt,
            'initial_evaluations': [
                {
                    'name': e.name,
                    'description': e.description,
                    'initial_page': e.initial_page,
                    'steps_count': len(e.steps)
                }
                for e in scenario.initial_evaluations
            ],
            'followup_evaluations': [
                {
                    'name': e.name,
                    'description': e.description,
                    'initial_page': e.initial_page,
                    'steps_count': len(e.steps)
                }
                for e in scenario.followup_evaluations
            ]
        } 