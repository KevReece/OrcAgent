#!/usr/bin/env python3
"""
Notion Utils for Benchmark Evaluations

Provides utilities for dumping Notion page content during benchmark evaluations.
"""

import os
import json
import requests
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from logger.log_wrapper import get_logger

load_dotenv(override=True)

logger = get_logger("evaluations:notion", __name__)


def get_notion_client():
    """
    Get initialized Notion client.
    """
    try:
        api_key = os.getenv("NOTION_API_KEY")
        if not api_key:
            return None
        # Return a simple object with the API key since we're using direct requests
        return type('NotionClient', (), {'api_key': api_key})()
    except Exception:
        return None


class NotionEvaluator:
    """Notion utility for dumping page content during evaluations."""
    
    def __init__(self):
        self.client = get_notion_client()
        if not self.client:
            raise ValueError("NOTION_API_KEY environment variable is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.client.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"
        
        # Get the root page ID from environment
        self.root_page_id = os.getenv("NOTION_PAGE_ID")
        if not self.root_page_id:
            raise ValueError("NOTION_PAGE_ID environment variable is required")
    
    def dump_root_page(self, output_path: str) -> str:
        """
        Dump the content of the Notion root page.
        
        Args:
            output_path: Path where to save the page dump
            
        Returns:
            String indicating success or error
        """
        try:
            logger.info(f"Dumping Notion root page: {self.root_page_id}")
            
            # Get page properties
            page_url = f"{self.base_url}/pages/{self.root_page_id}"
            response = requests.get(page_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return f"Error getting page properties: {response.status_code} - {response.text}"
            
            page_data = response.json()
            
            # Get page content (blocks)
            blocks_url = f"{self.base_url}/blocks/{self.root_page_id}/children"
            response = requests.get(blocks_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return f"Error getting page blocks: {response.status_code} - {response.text}"
            
            blocks_data = response.json()
            
            # Combine page data and blocks
            page_dump = {
                "page_properties": page_data,
                "page_blocks": blocks_data,
                "dump_timestamp": str(Path().cwd() / "timestamp"),
                "root_page_id": self.root_page_id
            }
            
            # Save to file
            dump_path = Path(output_path)
            dump_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(dump_path, 'w') as f:
                json.dump(page_dump, f, indent=2, default=str)
            
            logger.info(f"Notion page dump saved to: {dump_path}")
            return f"Notion page dump saved to: {dump_path}"
            
        except Exception as e:
            error_msg = f"Failed to dump Notion page: {e}"
            logger.error(error_msg)
            return error_msg
    
    def get_page_summary(self) -> str:
        """
        Get a summary of the Notion root page content.
        
        Returns:
            String containing page summary or error message
        """
        try:
            logger.info(f"Getting Notion root page summary: {self.root_page_id}")
            
            # Get page properties
            page_url = f"{self.base_url}/pages/{self.root_page_id}"
            response = requests.get(page_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return f"Error getting page properties: {response.status_code} - {response.text}"
            
            page_data = response.json()
            
            # Get page content (blocks)
            blocks_url = f"{self.base_url}/blocks/{self.root_page_id}/children"
            response = requests.get(blocks_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return f"Error getting page blocks: {response.status_code} - {response.text}"
            
            blocks_data = response.json()
            
            # Extract summary information
            title = "Unknown"
            if "properties" in page_data and "title" in page_data["properties"]:
                title_prop = page_data["properties"]["title"]
                if "title" in title_prop and title_prop["title"]:
                    title = title_prop["title"][0]["text"]["content"]
            
            # Count blocks by type
            block_types: Dict[str, int] = {}
            total_blocks = len(blocks_data.get("results", []))
            
            for block in blocks_data.get("results", []):
                block_type = block.get("type", "unknown")
                block_types[block_type] = block_types.get(block_type, 0) + 1
            
            # Create summary
            summary = f"Notion Root Page Summary:\n"
            summary += f"Title: {title}\n"
            summary += f"Page ID: {self.root_page_id}\n"
            summary += f"Total Blocks: {total_blocks}\n"
            summary += f"Block Types: {dict(block_types)}\n"
            
            return summary
            
        except Exception as e:
            error_msg = f"Failed to get Notion page summary: {e}"
            logger.error(error_msg)
            return error_msg


def dump_notion_root_page(output_path: str) -> str:
    """
    Convenience function to dump the Notion root page content.
    
    Args:
        output_path: Path where to save the page dump
        
    Returns:
        String indicating success or error
    """
    try:
        evaluator = NotionEvaluator()
        return evaluator.dump_root_page(output_path)
    except Exception as e:
        return f"Failed to initialize Notion evaluator: {e}"


def get_notion_page_summary() -> str:
    """
    Convenience function to get a summary of the Notion root page.
    
    Returns:
        String containing page summary or error message
    """
    try:
        evaluator = NotionEvaluator()
        return evaluator.get_page_summary()
    except Exception as e:
        return f"Failed to initialize Notion evaluator: {e}" 