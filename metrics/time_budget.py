#!/usr/bin/env python3
"""
Time Budget Utilities

Pure helpers to annotate responses with a time tag and enforce a prompt-based limit.
"""

from typing import Any, Optional
import math


def build_time_tag(current_count: int, max_count: int) -> str:
    """Create the standardized time tag string."""
    return f"(time: {current_count} of {max_count})"

def _is_tag_line(line: str) -> bool:
    return line.startswith("(time: ") or line.startswith("(overtime: ")

def _strip_existing_tag(text: str) -> str:
    if not text:
        return text
    # Remove a single leading tag line if present
    parts = text.split("\n", 1)
    if parts and _is_tag_line(parts[0]):
        return parts[1] if len(parts) > 1 else ""
    return text


def annotate_and_maybe_terminate(
    result: Any,
    current_count: int,
    max_count: int,
    metrics_tracker: Optional[Any] = None,
) -> Any:
    """
    Prepend the time tag to the given result. If the limit has been reached,
    set the metrics flag and return a termination message.
    """
    time_tag = build_time_tag(current_count, max_count)

    # Compute hard limit as 10% over soft budget (rounded up)
    hard_limit = int(math.ceil(max_count * 1.1))

    # Terminate at hard limit
    if current_count >= hard_limit:
        if metrics_tracker is not None:
            try:
                metrics_tracker.record_time_limit_prompts_reached()
            except Exception:
                pass
        overtime_tag = f"(overtime: {current_count} of hard limit {hard_limit})"
        return f"{overtime_tag}\nTERMINATE"

    # Between soft and hard limit: show overtime tag
    if current_count >= max_count:
        if metrics_tracker is not None:
            try:
                metrics_tracker.record_time_limit_prompts_reached()
            except Exception:
                pass
        overtime_tag = f"(overtime: {current_count} of hard limit {hard_limit})"
        time_tag = overtime_tag

    # Prepend the time or overtime tag, normalizing any existing tag
    if isinstance(result, str):
        normalized = _strip_existing_tag(result)
        return f"{time_tag}\n{normalized}" if normalized else time_tag
    if isinstance(result, dict) and "content" in result:
        if isinstance(result["content"], str):
            normalized = _strip_existing_tag(result["content"])
            result["content"] = f"{time_tag}\n{normalized}" if normalized else time_tag
        else:
            # For None or non-string content, set the tag as content
            result["content"] = time_tag
        return result
    if hasattr(result, "content"):
        content_val = getattr(result, "content", None)
        if isinstance(content_val, str):
            normalized = _strip_existing_tag(content_val)
            setattr(result, "content", f"{time_tag}\n{normalized}" if normalized else time_tag)
        else:
            setattr(result, "content", time_tag)
        return result

    return time_tag + "\n" + result if result else time_tag


