#!/usr/bin/env python3
"""
Playwright Utils for Benchmark Evaluations

Provides utilities for taking screenshots of deployed applications
during benchmark evaluations.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

from logger.log_wrapper import get_logger

load_dotenv(override=True)

logger = get_logger("evaluations:playwright", __name__)


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


class PlaywrightEvaluator:
    """Playwright utility for taking evaluation screenshots."""
    
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Ensure browsers are installed
        if not _ensure_browsers_installed():
            raise Exception("Failed to install Playwright browsers")
    
    def _initialize_playwright(self):
        """Initialize Playwright browser instance"""
        try:
            if self._playwright is None:
                self._playwright = sync_playwright().start()
            if self._browser is None:
                self._browser = self._playwright.chromium.launch(headless=True)
            if self._context is None:
                self._context = self._browser.new_context()
            if self._page is None:
                self._page = self._context.new_page()
            logger.info("Playwright browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise
    
    def _ensure_browser(self):
        """Ensure browser is initialized"""
        if not self._playwright or not self._browser or not self._context or not self._page:
            self._initialize_playwright()
    
    def take_prod_screenshot(self, output_path: str, url: Optional[str] = None) -> str:
        """
        Take a screenshot of the production ELB root page.
        
        Args:
            output_path: Path where to save the screenshot
            url: URL to screenshot (if not provided, uses AWS CLI to get prod URL)
            
        Returns:
            String indicating success or error
        """
        try:
            self._ensure_browser()
            
            # If no URL provided, get it from AWS CLI
            if not url:
                from benchmarking.evaluations.aws_cli_utils import get_prod_load_balancer_url
                url = get_prod_load_balancer_url()
                if not url or url.startswith("Error"):
                    return f"Failed to get prod URL: {url}"
            
            logger.info(f"Taking screenshot of: {url}")
            
            # Ensure page is initialized
            if self._page is None:
                return "Error: Page not initialized"
            
            # Navigate to the page
            self._page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait a bit for any dynamic content to load
            self._page.wait_for_timeout(2000)
            
            # Take full page screenshot
            screenshot_path = Path(output_path)
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._page.screenshot(path=str(screenshot_path), full_page=True)
            
            logger.info(f"Screenshot saved to: {screenshot_path}")
            return f"Screenshot saved to: {screenshot_path}"
            
        except Exception as e:
            error_msg = f"Failed to take screenshot: {e}"
            logger.error(error_msg)
            return error_msg
    
    def cleanup(self):
        """Clean up Playwright resources"""
        try:
            if self._page:
                self._page.close()
                self._page = None
            if self._context:
                self._context.close()
                self._context = None
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            logger.info("Playwright resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def take_prod_screenshot(output_path: str, url: Optional[str] = None) -> str:
    """
    Convenience function to take a screenshot of the production ELB root page.
    
    Args:
        output_path: Path where to save the screenshot
        url: URL to screenshot (if not provided, uses AWS CLI to get prod URL)
        
    Returns:
        String indicating success or error
    """
    evaluator = PlaywrightEvaluator()
    try:
        return evaluator.take_prod_screenshot(output_path, url)
    finally:
        evaluator.cleanup() 