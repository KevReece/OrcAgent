#!/usr/bin/env python3
"""
Test Playwright Tools Module

Integration tests for Playwright tools using example.com
"""

import unittest
import os
import shutil
import tempfile
from tools.playwright_tools import get_tools
from tools.context import ToolsContext


def make_tools_context(tmp_path):
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir=str(tmp_path),
        is_integration_test=True
    )


class TestPlaywrightTools(unittest.TestCase):
    
    def setUp(self):
        """Set up a temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp(prefix="playwright_test_")
        tools = get_tools(make_tools_context(self.test_dir))
        
        class Self:
            def __init__(self, tools):
                self.navigate_to_url = tools[0]
                self.get_page_content = tools[1]
                self.get_page_title = tools[2]
                self.take_screenshot = tools[3]
                self.click_element = tools[4]
                self.fill_input = tools[5]
                self.get_element_text = tools[6]
                self.wait_for_element = tools[7]
                self.get_page_url = tools[8]
                self.evaluate_javascript = tools[9]
                self.get_page_source = tools[10]
                self.close_current_page = tools[11]
                self.cleanup = tools[12]
        
        self.playwright_tools = Self(tools)

    def tearDown(self):
        """Clean up the temporary directory and Playwright resources."""
        # Proper cleanup of all playwright resources
        try:
            self.playwright_tools.cleanup()
        except Exception:
            pass  # Ignore cleanup errors
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_navigate_to_example_com(self):
        """Test navigating to example.com."""
        result = self.playwright_tools.navigate_to_url("https://example.com")
        self.assertIn("Successfully navigated", result)
        self.assertIn("example.com", result)

    def test_get_page_title(self):
        """Test getting the page title from example.com."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Get the title
        title = self.playwright_tools.get_page_title()
        self.assertIn("Example", title)

    def test_get_page_content(self):
        """Test getting page content from example.com."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Get content
        content = self.playwright_tools.get_page_content()
        self.assertIn("html", content.lower())
        self.assertIn("example", content.lower())

    def test_get_page_url(self):
        """Test getting the current page URL."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Get URL
        url = self.playwright_tools.get_page_url()
        self.assertIn("example.com", url)

    def test_take_screenshot(self):
        """Test taking a screenshot of example.com."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Take screenshot
        result = self.playwright_tools.take_screenshot("test_screenshot.png")
        self.assertIn("Screenshot saved successfully", result)
        
        # Verify file exists
        screenshot_path = os.path.join(self.test_dir, "test_screenshot.png")
        self.assertTrue(os.path.exists(screenshot_path))
        
        # Verify file is not empty
        self.assertGreater(os.path.getsize(screenshot_path), 0)

    def test_get_element_text(self):
        """Test getting text from an element on example.com."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Get text from h1 element (example.com has an h1 with "Example Domain")
        text = self.playwright_tools.get_element_text("h1")
        self.assertIn("Example", text)

    def test_evaluate_javascript(self):
        """Test executing JavaScript on example.com."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Execute simple JavaScript
        result = self.playwright_tools.evaluate_javascript("document.title")
        self.assertIn("Example", result)

    def test_get_page_source(self):
        """Test getting page source (alias for get_page_content)."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Get source
        source = self.playwright_tools.get_page_source()
        self.assertIn("html", source.lower())
        self.assertIn("example", source.lower())

    def test_wait_for_element(self):
        """Test waiting for an element to appear."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Wait for h1 element (should already be there)
        result = self.playwright_tools.wait_for_element("h1", timeout=5000)
        self.assertIn("Element h1 appeared", result)

    def test_close_current_page(self):
        """Test closing the current page."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Close the page
        result = self.playwright_tools.close_current_page()
        self.assertIn("Current page closed successfully", result)
        
        # Try to get content after closing (should fail)
        content_result = self.playwright_tools.get_page_content()
        self.assertIn("Error: No page is currently loaded", content_result)

    def test_no_page_loaded_errors(self):
        """Test that appropriate errors are returned when no page is loaded."""
        # Close the current page first if any
        self.playwright_tools.close_current_page()
        
        # These should all return error messages
        content_result = self.playwright_tools.get_page_content()
        self.assertIn("Error: No page is currently loaded", content_result)
        
        title_result = self.playwright_tools.get_page_title()
        self.assertIn("Error: No page is currently loaded", title_result)
        
        screenshot_result = self.playwright_tools.take_screenshot()
        self.assertIn("Error: No page is currently loaded", screenshot_result)
        
        click_result = self.playwright_tools.click_element("h1")
        self.assertIn("Error: No page is currently loaded", click_result)
        
        fill_result = self.playwright_tools.fill_input("input", "test")
        self.assertIn("Error: No page is currently loaded", fill_result)
        
        text_result = self.playwright_tools.get_element_text("h1")
        self.assertIn("Error: No page is currently loaded", text_result)
        
        wait_result = self.playwright_tools.wait_for_element("h1")
        self.assertIn("Error: No page is currently loaded", wait_result)
        
        url_result = self.playwright_tools.get_page_url()
        self.assertIn("Error: No page is currently loaded", url_result)
        
        js_result = self.playwright_tools.evaluate_javascript("document.title")
        self.assertIn("Error: No page is currently loaded", js_result)

    def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        result = self.playwright_tools.navigate_to_url("invalid-url")
        self.assertIn("Error navigating", result)

    def test_invalid_selector_handling(self):
        """Test handling of invalid CSS selectors."""
        # First navigate to a valid page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Try to get text from non-existent element with short timeout (1 second)
        result = self.playwright_tools.get_element_text("nonexistent-element", timeout=1000)
        # This should return an error message due to timeout
        self.assertIsInstance(result, str)
        self.assertIn("Error getting text", result)

    def test_screenshot_with_subdirectory(self):
        """Test taking a screenshot with a subdirectory path."""
        # First navigate to the page
        self.playwright_tools.navigate_to_url("https://example.com")
        
        # Take screenshot in subdirectory
        result = self.playwright_tools.take_screenshot("screenshots/test.png")
        self.assertIn("Screenshot saved successfully", result)
        
        # Verify file exists
        screenshot_path = os.path.join(self.test_dir, "screenshots", "test.png")
        self.assertTrue(os.path.exists(screenshot_path))


if __name__ == '__main__':
    unittest.main() 