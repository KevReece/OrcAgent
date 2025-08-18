#!/usr/bin/env python3
"""
GitHub Actions Wait Utils for Benchmark Evaluations

Provides a decoupled utility to wait for active GitHub Actions workflows
to complete in the current repository. This file intentionally duplicates
the waiting logic to avoid coupling the benchmarking layer to the tools layer.
"""

import time
import os
from logger.log_wrapper import get_logger
from tools.gh_helper import run_gh_command


logger = get_logger("evaluations:gh_actions_wait", __name__)


def wait_for_active_workflows(timeout_seconds: int = 900, poll_interval_seconds: int = 10) -> str:
    """
    Wait for all active GitHub Actions workflow runs in the current repository to complete.

    Args:
        timeout_seconds: Maximum time to wait before giving up.
        poll_interval_seconds: Delay between checks.

    Returns:
        str: Summary message indicating completion, timeout, or error details.
    """
    if timeout_seconds <= 0:
        return "Error: timeout_seconds must be positive"
    if poll_interval_seconds <= 0:
        return "Error: poll_interval_seconds must be positive"

    deadline = time.time() + timeout_seconds

    list_result = run_gh_command(["run", "list", "--limit", "50"], cwd=os.getcwd())
    if "Error" in list_result:
        return list_result

    def has_active_runs(output: str) -> bool:
        lower = output.lower()
        indicators = ["in_progress", "in progress", "queued", "waiting"]
        return any(ind in lower for ind in indicators)

    if not has_active_runs(list_result):
        logger.info("No active GitHub Actions workflow runs found")
        return "No active GitHub Actions workflow runs found"

    logger.info("Active GitHub Actions workflow runs detected. Waiting for completion...")
    while time.time() < deadline:
        time.sleep(poll_interval_seconds)
        result = run_gh_command(["run", "list", "--limit", "50"], cwd=os.getcwd())
        if "Error" in result:
            return result
        if not has_active_runs(result):
            logger.info("All GitHub Actions workflow runs have completed")
            return "All GitHub Actions workflow runs have completed"

    logger.info("Timeout waiting for GitHub Actions workflows to complete")
    return "Timeout waiting for GitHub Actions workflows to complete"


