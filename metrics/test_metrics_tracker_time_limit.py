#!/usr/bin/env python3
"""
Integration tests for MetricsTracker time limit flag persistence.
"""

import json
import os
from metrics.metrics_tracker import MetricsTracker


def test_time_limit_flag_saved(tmp_path):
    run_dir = tmp_path.as_posix()
    tracker = MetricsTracker(run_dir)

    # Simulate runtime
    tracker.start_execution(model="gpt-5", agents_mode="team", prompt="x")
    tracker.record_time_limit_prompts_reached()
    tracker.complete_execution(success=False, error_message=None)

    # Save and read back
    path = tracker.save_metrics("metrics.json")
    assert os.path.exists(path)

    with open(path, "r") as f:
        data = json.load(f)

    assert data.get("time_limit_prompts_reached") is True


