#!/usr/bin/env python3
"""
Integration tests for web_tools using example.com
"""

import os
import shutil
import tempfile
import unittest

from tools.web_tools import get_tools
from tools.context import ToolsContext


def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True,
    )


class TestWebTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="web_tools_test_")
        tools = get_tools(make_tools_context(self.test_dir))

        class Self:
            def __init__(self, tools):
                self.web_request = tools[0]

        self.web_tools = Self(tools)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_web_request_example_com(self):
        result = self.web_tools.web_request("https://example.com")
        self.assertIsInstance(result, str)
        self.assertIn("Example Domain", result)

    def test_web_request_invalid_url(self):
        result = self.web_tools.web_request("http://nonexistent.invalid")
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("Error:"))


if __name__ == "__main__":
    unittest.main()


