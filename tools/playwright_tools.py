#!/usr/bin/env python3
"""
Playwright Tools Module

This module provides Playwright automation tools for browser interaction.
"""

import os
import subprocess
import sys
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

from typing import List, Callable
from logger.log_wrapper import get_logger
from tools.context import ToolsContext

logger = get_logger("tool:playwright", __name__)


def _ensure_browsers_installed():
    """Ensure Playwright browsers are installed"""
    try:
        logger.info("Checking if Playwright browsers are installed...")
        # Try to start playwright to check if browsers are available
        pw = sync_playwright().start()
        try:
            # Try to launch chromium to test if it's installed
            browser = pw.chromium.launch(headless=True)
            browser.close()
            pw.stop()
            logger.info("Playwright browsers are already installed")
            return True
        except Exception:
            pw.stop()
            logger.info("Playwright browsers not found, installing...")
            return _install_browsers()
    except Exception as e:
        logger.error(f"Error checking browser installation: {e}")
        return _install_browsers()


def _install_browsers():
    """Install Playwright browsers programmatically"""
    try:
        logger.info("Installing Playwright browsers...")
        # Use subprocess to install browsers
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            logger.info("Playwright browsers installed successfully")
            return True
        else:
            logger.error(f"Browser installation failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Browser installation timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to install browsers: {e}")
        return False


# Global flag to track if browsers have been checked/installed
_browsers_checked = False


def get_tools(tools_context: ToolsContext):
    """Playwright browser automation tools for agents"""
    
    def _ensure_setup():
        """Ensure browsers are installed and initialize if needed"""
        global _browsers_checked
        if not _browsers_checked:
            if not _ensure_browsers_installed():
                raise Exception("Failed to install Playwright browsers")
            _browsers_checked = True

    def _initialize_playwright():
        """Initialize Playwright browser instance"""
        try:
            if self._playwright is None:
                self._playwright = sync_playwright().start()
            if self._browser is None:
                self._browser = self._playwright.chromium.launch(headless=True)
            if self._context is None:
                self._context = self._browser.new_context()
            logger.info("Playwright browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

    def _ensure_browser():
        """Ensure browser is initialized"""
        if not self._playwright or not self._browser or not self._context:
            _initialize_playwright()
    
    def init(self, agent_work_dir: str):
        self.agent_work_dir = agent_work_dir
        self._playwright = None
        self._browser = None
        self._context = None
        self._current_page = None
        _ensure_setup()
    
    self = type("Self", (), {})()
    init(self, tools_context.agent_work_dir)

    def playwright_navigate_to_url(url: str) -> str:
        """Navigate to a URL and return success/error status."""
        try:
            if not self._playwright or not self._browser or not self._context:
                _initialize_playwright()
            if not self._context:
                return "Error: Browser context not available."
            
            if self._current_page:
                self._current_page.close()
            
            self._current_page = self._context.new_page()
            self._current_page.goto(url, timeout=30000)  # 30 second timeout
            title = self._current_page.title()
            logger.info(f"Successfully navigated to {url}")
            return f"Successfully navigated to {url}. Page title: {title}"
        except Exception as e:
            error_msg = f"Error navigating to {url}: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_get_page_content() -> str:
        """Get the HTML content of the current page."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            content = self._current_page.content()
            return content
        except Exception as e:
            error_msg = f"Error getting page content: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_get_page_title() -> str:
        """Get the title of the current page."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            title = self._current_page.title()
            return title
        except Exception as e:
            error_msg = f"Error getting page title: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_take_screenshot(filename: str = "screenshot.png", full_page: bool = True) -> str:
        """Take a screenshot of the current page and save it to the agent's working directory."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            filepath = os.path.join(self.agent_work_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            self._current_page.screenshot(path=filepath, full_page=full_page)
            logger.info(f"Screenshot saved to {filepath}")
            return f"Screenshot saved successfully to {filename}"
        except Exception as e:
            error_msg = f"Error taking screenshot: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_click_element(selector: str) -> str:
        """Click an element on the current page using CSS selector."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            self._current_page.click(selector)
            logger.info(f"Successfully clicked element: {selector}")
            return f"Successfully clicked element: {selector}"
        except Exception as e:
            error_msg = f"Error clicking element {selector}: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_fill_input(selector: str, text: str) -> str:
        """Fill an input field with text using CSS selector."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            self._current_page.fill(selector, text)
            logger.info(f"Successfully filled input {selector} with text")
            return f"Successfully filled input {selector} with text"
        except Exception as e:
            error_msg = f"Error filling input {selector}: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_get_element_text(selector: str, timeout: int = 5000) -> str:
        """Get the text content of an element using CSS selector."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            element = self._current_page.locator(selector)
            text = element.text_content(timeout=timeout)
            return text if text else ""
        except Exception as e:
            error_msg = f"Error getting text from element {selector}: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_wait_for_element(selector: str, timeout: int = 30000) -> str:
        """Wait for an element to appear on the page using CSS selector."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            self._current_page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"Element {selector} appeared on page")
            return f"Element {selector} appeared on page"
        except Exception as e:
            error_msg = f"Error waiting for element {selector}: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_get_page_url() -> str:
        """Get the current page URL."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            url = self._current_page.url
            return url
        except Exception as e:
            error_msg = f"Error getting page URL: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_evaluate_javascript(script: str) -> str:
        """Execute JavaScript code on the current page and return the result."""
        try:
            if not self._current_page:
                return "Error: No page is currently loaded. Use navigate_to_url first."
            
            result = self._current_page.evaluate(script)
            return str(result)
        except Exception as e:
            error_msg = f"Error executing JavaScript: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_get_page_source() -> str:
        """Get the page source (same as get_page_content but with different name for clarity)."""
        return playwright_get_page_content()

    def playwright_close_current_page() -> str:
        """Close the current page."""
        try:
            if self._current_page:
                self._current_page.close()
                self._current_page = None
                logger.info("Current page closed successfully")
                return "Current page closed successfully"
            else:
                return "No page is currently open"
        except Exception as e:
            error_msg = f"Error closing page: {e}"
            logger.error(error_msg)
            return error_msg

    def playwright_cleanup():
        """Clean up Playwright resources"""
        try:
            if self._current_page:
                self._current_page.close()
                self._current_page = None
            if self._context:
                self._context.close()
                self._context = None
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
        except Exception as e:
            pass  # Ignore cleanup errors
    
    # Return tool methods as a list
    return [
        playwright_navigate_to_url,
        playwright_get_page_content,
        playwright_get_page_title,
        playwright_take_screenshot,
        playwright_click_element,
        playwright_fill_input,
        playwright_get_element_text,
        playwright_wait_for_element,
        playwright_get_page_url,
        playwright_evaluate_javascript,
        playwright_get_page_source,
        playwright_close_current_page,
        playwright_cleanup,
    ] 