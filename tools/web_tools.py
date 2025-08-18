#!/usr/bin/env python3
"""
Web Tools Module

This module provides lightweight web utilities for validation and testing.
Currently includes a simple curl-like HTTP request function.
"""

from typing import Optional, Dict
import json

import requests

from logger.log_wrapper import get_logger
from tools.context import ToolsContext


logger = get_logger("tool:web", __name__)


def get_tools(tools_context: ToolsContext):
    """Web tools available to agents"""

    def init(self, agent_work_dir: str):
        self.agent_work_dir = agent_work_dir

    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir)

    def web_request(url: str, method: str = "GET", headers_json: Optional[str] = None, body: Optional[str] = None, timeout_seconds: int = 30) -> str:
        """
        Perform a simple HTTP request similar to curl.

        Args:
            url: The URL to request.
            method: HTTP method, defaults to GET.
            headers_json: Optional JSON string of headers.
            body: Optional string body for POST/PUT/PATCH.
            timeout_seconds: Request timeout in seconds.

        Returns:
            On success: response text (body).
            On failure: an error message starting with 'Error:'.
        """
        try:
            headers: Optional[Dict[str, str]] = None
            if headers_json:
                try:
                    headers = json.loads(headers_json)
                except Exception as e:
                    return f"Error: Invalid headers JSON - {e}"

            logger.info(f"HTTP {method} {url}")
            response = requests.request(method=method.upper(), url=url, headers=headers, data=body, timeout=timeout_seconds)
            # Raise for HTTP error codes to surface issues clearly
            try:
                response.raise_for_status()
            except Exception as e:
                # Still return the body (often useful for debugging) but signal error
                return f"Error: HTTP {response.status_code} - {e}\n{response.text}"
            return response.text
        except requests.Timeout:
            return "Error: Request timed out"
        except requests.RequestException as e:
            return f"Error: Request failed - {e}"
        except Exception as e:
            return f"Error: Unexpected failure - {e}"

    return [
        web_request,
    ]


