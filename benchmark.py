#!/usr/bin/env python3
"""
Benchmark - Main Entry Point

Enterprise-grade benchmark system for evaluating agent performance
across different complexity levels and scenarios.
"""

import argparse
import sys
import traceback
from datetime import datetime

from benchmarking.benchmark_runner import BenchmarkRunner
from benchmarking.benchmark_scenarios import create_benchmark_scenarios
from logger.log_wrapper import get_logger


def _parse_comma_separated_list(value: str) -> list:
    """Parse a comma-separated string into a list, stripping whitespace."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _validate_agent_modes(agent_modes: list) -> list:
    """Validate agent modes and return the list of valid modes."""
    valid_modes = ["solo", "pair", "team", "company", "orchestrator", 
                   "orchestrator-small-minimal", "orchestrator-small-balanced", "orchestrator-small-extensive", 
                   "orchestrator-medium-minimal", "orchestrator-medium-balanced", "orchestrator-medium-extensive", 
                   "orchestrator-large-minimal", "orchestrator-large-balanced", "orchestrator-large-extensive"]
    
    invalid_modes = [mode for mode in agent_modes if mode not in valid_modes]
    if invalid_modes:
        raise ValueError(f"Invalid agent mode(s): {', '.join(invalid_modes)}. Valid modes are: {', '.join(valid_modes)}")
    
    return agent_modes


def _validate_scenario_ids(scenario_ids: list) -> list:
    """Validate scenario IDs and return the list of valid IDs."""
    available_scenarios = create_benchmark_scenarios()
    available_ids = [scenario.id for scenario in available_scenarios]
    
    invalid_ids = [scenario_id for scenario_id in scenario_ids if scenario_id not in available_ids]
    if invalid_ids:
        raise ValueError(f"Invalid scenario ID(s): {', '.join(invalid_ids)}. Available scenarios: {', '.join(available_ids)}")
    
    return scenario_ids


def _log_execution_summary(scenarios_to_run: list, agent_modes: list, model: str, base_output_dir: str):
    """Log a comprehensive summary of what will be executed."""
    logger = get_logger("benchmark:summary", __name__)
    
    print("=" * 80)
    print("BENCHMARK EXECUTION SUMMARY")
    print("=" * 80)
    print()
    
    print(f"MODEL: {model}")
    print(f"OUTPUT DIRECTORY: {base_output_dir}")
    print()
    
    print(f"AGENT MODES ({len(agent_modes)}):")
    print("-" * 20)
    for i, mode in enumerate(agent_modes, 1):
        print(f"  {i}. {mode}")
    print()
    
    if scenarios_to_run:
        print(f"SCENARIOS TO EXECUTE ({len(scenarios_to_run)}):")
        print("-" * 30)
        for i, scenario_id in enumerate(scenarios_to_run, 1):
            print(f"  {i}. {scenario_id}")
    else:
        print("SCENARIOS: All available scenarios (excluding test complexity)")
    print()
    
    total_scenarios = len(scenarios_to_run) if scenarios_to_run else len([s for s in create_benchmark_scenarios() if s.complexity.value != 'test'])
    print(f"TOTAL EXECUTIONS: {len(agent_modes) * total_scenarios}")
    print()
    print("=" * 80)
    print()
    
    logger.info(f"Starting benchmark execution with {len(agent_modes)} agent mode(s) and {len(scenarios_to_run) if scenarios_to_run else 'all'} scenario(s)")


def main():
    """Main entry point for the benchmark system."""
    parser = argparse.ArgumentParser(
        description="OrcAgent Benchmark System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark.py --list-scenarios                    # List all available scenarios
  python benchmark.py --scenario solo-electrician-website --agents=solo  # Run single scenario
  python benchmark.py --scenario solo-electrician-website,chicken-farming-blog --agents=solo,pair  # Run multiple scenarios with multiple agent modes
  python benchmark.py --agents=team                       # Run all scenarios (default)
  python benchmark.py --complexity small --agents=pair    # Run all small scenarios
  python benchmark.py --scenario chicken-farming-blog --agents=company  # Run with company agents
  python benchmark.py --agents=orchestrator --model=gpt-4o  # Run with custom model
  python benchmark.py --scenario solo-electrician-website,chicken-farming-blog --agents=solo,team,company  # Run multiple scenarios with multiple agent modes
        """
    )
    
    # Main action arguments
    action_group = parser.add_mutually_exclusive_group(required=False)
    action_group.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List all available benchmark scenarios"
    )
    action_group.add_argument(
        "--scenario",
        type=str,
        help="Run specific scenario(s) by ID (comma-separated for multiple)"
    )
    action_group.add_argument(
        "--complexity",
        type=str,
        choices=["small", "medium", "large", "enterprise", "test"],
        help="Run all scenarios of a specific complexity level"
    )
    
    # Required configuration arguments
    parser.add_argument(
        "--agents",
        type=str,
        help="Choose agent initialization mode(s) (comma-separated for multiple). Valid modes: solo, pair, team, company, orchestrator, orchestrator-(small|medium|large)-(minimal|balanced|extensive)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5",
        help="LLM model to use (defaults to 'gpt-5)"
    )
    
    parser.add_argument(
        "--scenario-details",
        type=str,
        help="Show detailed information about a specific scenario"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = get_logger("benchmark:main", __name__)
    
    try:
        # Parse and validate agent modes
        if args.agents == "orchestrators":
            agent_modes = ["orchestrator-small-minimal", "orchestrator-small-balanced", "orchestrator-small-extensive", 
                 "orchestrator-medium-minimal", "orchestrator-medium-balanced", "orchestrator-medium-extensive", 
                 "orchestrator-large-minimal", "orchestrator-large-balanced", "orchestrator-large-extensive"]
        elif args.agents:
            agent_modes = _validate_agent_modes(_parse_comma_separated_list(args.agents))
        else:
            agent_modes = ["solo", "pair", "team", "company", "orchestrator"]
        
        # Parse and validate scenario IDs if specified
        scenarios_to_run = None
        if args.scenario:
            scenarios_to_run = _validate_scenario_ids(_parse_comma_separated_list(args.scenario))
        
        # Initialize benchmark runner with timestamp-based output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = f"benchmarking/results/{timestamp}"
        
        # Create the base directory structure
        from pathlib import Path
        base_path = Path(base_output_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Log execution summary before starting
        _log_execution_summary(scenarios_to_run, agent_modes, args.model, base_output_dir)
        
        if args.scenario_details:
            _show_scenario_details(args.scenario_details)
        elif args.list_scenarios:
            _list_scenarios()
        elif scenarios_to_run:
            _run_multiple_scenarios_all_agents(scenarios_to_run, agent_modes, args.model, base_output_dir)
        elif args.complexity:
            _run_complexity_scenarios_all_agents(args.complexity, agent_modes, args.model, base_output_dir)
        else:
            # Default: run all scenarios
            _run_all_scenarios_all_agents(agent_modes, args.model, base_output_dir)
            
    except KeyboardInterrupt:
        logger.info("Benchmark execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Benchmark execution failed: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)


def _list_scenarios():
    """List all available scenarios (excluding test complexity by default)."""
    scenarios = create_benchmark_scenarios()
    # Filter out test complexity scenarios for default listing
    scenarios = [s for s in scenarios if s.complexity.value != "test"]
    
    print("AVAILABLE BENCHMARK SCENARIOS")
    print("=" * 50)
    print()
    
    # Group by complexity
    complexity_groups = {}
    for scenario in scenarios:
        complexity = scenario.complexity.value
        if complexity not in complexity_groups:
            complexity_groups[complexity] = []
        complexity_groups[complexity].append(scenario)
    
    for complexity in ["small", "medium", "large", "enterprise"]:
        if complexity in complexity_groups:
            print(f"{complexity.upper()} COMPLEXITY SCENARIOS")
            print("-" * 30)
            
            for scenario in complexity_groups[complexity]:
                print(f"ID: {scenario.id}")
                print(f"Initial Evaluations: {len(scenario.initial_evaluations)}")
                print(f"Followup Evaluations: {len(scenario.followup_evaluations)}")
                print()
    
    print(f"Total scenarios: {len(scenarios)}")
    print("Note: Test complexity scenarios are excluded by default. Use --complexity test to see them.")


def _show_scenario_details(scenario_id: str):
    """Show detailed information about a specific scenario."""
    runner = BenchmarkRunner()
    details = runner.get_scenario_details(scenario_id)
    
    if not details:
        print(f"Scenario not found: {scenario_id}")
        sys.exit(1)
    
    print(f"SCENARIO DETAILS: {details['id']}")
    print("=" * 50)
    print()
    
    print(f"ID: {details['id']} | Complexity: {details['complexity']}")
    print()
    
    print("INITIAL PROMPT:")
    print("-" * 15)
    print(details['initial_prompt'])
    print()
    
    print("FOLLOW-UP PROMPT:")
    print("-" * 18)
    print(details['follow_up_prompt'])
    print()
    
    print("INITIAL EVALUATIONS:")
    print("-" * 20)
    for i, evaluation in enumerate(details['initial_evaluations'], 1):
        print(f"{i}. {evaluation['name']} | Steps: {evaluation['steps_count']}")
        print(f"   Description: {evaluation['description']}")
        print(f"   Initial Page: {evaluation['initial_page']}")
        print()
    
    print("FOLLOWUP EVALUATIONS:")
    print("-" * 22)
    for i, evaluation in enumerate(details['followup_evaluations'], 1):
        print(f"{i}. {evaluation['name']} | Steps: {evaluation['steps_count']}")
        print(f"   Description: {evaluation['description']}")
        print(f"   Initial Page: {evaluation['initial_page']}")
        print()


def _run_multiple_scenarios_all_agents(scenario_ids: list, agent_modes: list, model: str, base_output_dir: str):
    """Run multiple specific scenarios for all agent modes."""
    logger = get_logger("benchmark:multiple", __name__)
    
    print(f"Running {len(scenario_ids)} scenarios: {', '.join(scenario_ids)} | Agents: {', '.join(agent_modes)}")
    print()
    
    try:
        for agent_mode in agent_modes:
            print(f"Running with {agent_mode} agents...")
            output_dir = f"{base_output_dir}/{agent_mode}"
            runner = BenchmarkRunner(output_dir=output_dir)
            
            for i, scenario_id in enumerate(scenario_ids, 1):
                print(f"  [{i}/{len(scenario_ids)}] Running scenario: {scenario_id}")
                
                result = runner.run_single_scenario(scenario_id, agent_mode, model)
                
                print(f"    Scenario execution completed for {agent_mode} agents.")
                print(f"    Success: {'Yes' if result.passed_evaluations == result.total_evaluations else 'No'}")
                print(f"    Score: {result.total_score:.2f}/{result.max_possible_score:.2f} | Passed: {result.passed_evaluations}/{result.total_evaluations} | Time: {result.execution_time_minutes:.1f} min")
                print()
            
            print(f"All scenarios completed for {agent_mode} agents.")
            print("=" * 50)
            print(f"Results saved to: {runner.output_dir}")
            print("-" * 50)
            print()
        
    except Exception as e:
        logger.error(f"Failed to run scenarios {', '.join(scenario_ids)} for all agents: {e}")
        print(f"Error: {e}")
        sys.exit(1)


def _run_single_scenario_all_agents(scenario_id: str, agent_modes: list, model: str, base_output_dir: str):
    """Run a single scenario for all agent modes."""
    # This function is now deprecated in favor of _run_multiple_scenarios_all_agents
    # Keep for backward compatibility
    _run_multiple_scenarios_all_agents([scenario_id], agent_modes, model, base_output_dir)


def _run_all_scenarios_all_agents(agent_modes: list, model: str, base_output_dir: str):
    """Run all scenarios for all agent modes (excluding test complexity)."""
    logger = get_logger("benchmark:all", __name__)
    
    scenarios = create_benchmark_scenarios()
    # Filter out test complexity scenarios when running all scenarios
    scenarios = [s for s in scenarios if s.complexity.value != "test"]
    print(f"Running all {len(scenarios)} scenarios (excluding test complexity) | Agents: {', '.join(agent_modes)}")
    print()
    
    try:
        for agent_mode in agent_modes:
            print(f"Running all scenarios with {agent_mode} agents...")
            output_dir = f"{base_output_dir}/{agent_mode}"
            runner = BenchmarkRunner(output_dir=output_dir)
            
            results = runner.run_all_scenarios(agent_mode, model)
            
            print(f"{agent_mode.upper()} SCENARIOS COMPLETED")
            print("=" * 30)
            print()
            
            # Summary statistics
            successful = sum(1 for r in results if r.passed_evaluations == r.total_evaluations)
            total_score = sum(r.total_score for r in results)
            max_score = sum(r.max_possible_score for r in results)
            avg_time = sum(r.execution_time_minutes for r in results) / len(results) if results else 0
            
            print(f"Total: {len(results)} | Successful: {successful} | Failed: {len(results) - successful} | Success Rate: {(successful/len(results)*100):.1f}%")
            print(f"Average Score: {total_score/len(results):.2f}/{max_score/len(results):.2f} | Average Time: {avg_time:.1f} min")
            print()
            
            # Individual results
            print("INDIVIDUAL RESULTS:")
            print("-" * 18)
            for result in results:
                status = "PASS" if result.passed_evaluations == result.total_evaluations else "FAIL"
                print(f"{result.scenario_name}: {status} ({result.total_score:.2f}/{result.max_possible_score:.2f})")
            
            print()
            print(f"Detailed results saved to: {runner.output_dir}")
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"Failed to run all scenarios for all agents: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        print(f"Error: {e}")
        sys.exit(1)


def _run_complexity_scenarios_all_agents(complexity: str, agent_modes: list, model: str, base_output_dir: str):
    """Run scenarios of a specific complexity for all agent modes."""
    logger = get_logger("benchmark:complexity", __name__)
    
    print(f"Running {complexity} complexity scenarios | Agents: {', '.join(agent_modes)}")
    print()
    
    try:
        for agent_mode in agent_modes:
            print(f"Running {complexity} scenarios with {agent_mode} agents...")
            output_dir = f"{base_output_dir}/{agent_mode}"
            runner = BenchmarkRunner(output_dir=output_dir)
            
            results = runner.run_scenarios_by_complexity(complexity, agent_mode, model)
            
            print(f"{complexity.upper()} SCENARIOS COMPLETED for {agent_mode} agents")
            print("=" * 30)
            print()
            
            # Summary statistics
            successful = sum(1 for r in results if r.passed_evaluations == r.total_evaluations)
            total_score = sum(r.total_score for r in results)
            max_score = sum(r.max_possible_score for r in results)
            avg_time = sum(r.execution_time_minutes for r in results) / len(results) if results else 0
            
            print(f"Total: {len(results)} | Successful: {successful} | Failed: {len(results) - successful} | Success Rate: {(successful/len(results)*100):.1f}%")
            print(f"Average Score: {total_score/len(results):.2f}/{max_score/len(results):.2f} | Average Time: {avg_time:.1f} min")
            print()
            
            # Individual results
            print("INDIVIDUAL RESULTS:")
            print("-" * 18)
            for result in results:
                status = "PASS" if result.passed_evaluations == result.total_evaluations else "FAIL"
                print(f"{result.scenario_name}: {status} ({result.total_score:.2f}/{result.max_possible_score:.2f})")
            
            print()
            print(f"Detailed results saved to: {runner.output_dir}")
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"Failed to run {complexity} scenarios for all agents: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 