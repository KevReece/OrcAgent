#!/usr/bin/env python3
"""
Integration tests for time budget tagging and metrics flagging.
"""

import pytest

from metrics.time_budget import build_time_tag, annotate_and_maybe_terminate


class DummyMetrics:
    def __init__(self):
        self.called = False

    def record_time_limit_prompts_reached(self):
        self.called = True


def test_build_time_tag_formatting():
    assert build_time_tag(1, 100) == "(time: 1 of 100)"
    assert build_time_tag(0, 10) == "(time: 0 of 10)"


def test_annotate_non_terminating_string():
    res = annotate_and_maybe_terminate("Hello", current_count=5, max_count=10, metrics_tracker=None)
    assert res.startswith("(time: 5 of 10)\n")
    assert res.endswith("Hello")


def test_annotate_non_terminating_dict():
    res = annotate_and_maybe_terminate({"content": "Hi"}, current_count=2, max_count=3, metrics_tracker=None)
    assert isinstance(res, dict)
    assert res["content"].startswith("(time: 2 of 3)\n")
    assert res["content"].endswith("Hi")


def test_annotate_terminating_string_sets_flag_and_returns_TERMINATE():
    dummy = DummyMetrics()
    res = annotate_and_maybe_terminate("Anything", current_count=100, max_count=100, metrics_tracker=dummy)
    assert dummy.called is True
    assert res == "(time: 100 of 100)\nTERMINATE"


def test_annotate_terminating_dict_sets_flag_and_returns_TERMINATE():
    dummy = DummyMetrics()
    res = annotate_and_maybe_terminate({"content": "Anything"}, current_count=3, max_count=3, metrics_tracker=dummy)
    assert dummy.called is True
    assert res == "(time: 3 of 3)\nTERMINATE"


def test_annotate_unknown_type_fallback_returns_time_tag_only():
    class Obj:
        def __str__(self):
            return "OBJ"

    obj = Obj()
    res = annotate_and_maybe_terminate(obj, current_count=7, max_count=10, metrics_tracker=None)
    assert res == "(time: 7 of 10)"


def test_annotate_dict_with_none_content_sets_time_tag():
    res = annotate_and_maybe_terminate({"content": None}, current_count=4, max_count=10, metrics_tracker=None)
    assert isinstance(res, dict)
    assert res["content"] == "(time: 4 of 10)"


def test_overtime_tag_between_soft_and_hard_limit_sets_flag_and_uses_overtime_format():
    dummy = DummyMetrics()
    # soft=10, hard=11 (ceil(10*1.1))
    res = annotate_and_maybe_terminate("x", current_count=10, max_count=10, metrics_tracker=dummy)
    assert dummy.called is True
    assert res.startswith("(overtime: 10 of hard limit 11)\n")


def test_hard_limit_terminates_with_overtime_tag():
    dummy = DummyMetrics()
    # soft=10, hard=11; at 11 we terminate
    res = annotate_and_maybe_terminate("x", current_count=11, max_count=10, metrics_tracker=dummy)
    assert dummy.called is True
    assert res == "(overtime: 11 of hard limit 11)\nTERMINATE"


