#!/usr/bin/env python3
"""
Unit tests for notion_page.py module.

This test file uses NOTION_TEST_PAGE_ID environment variable to avoid
interfering with the main Notion page used by the application.
"""

import unittest
import os
from agent_environment.notion_page_agent_environment import NotionPageAgentEnvironment as NotionPage


class TestNotionPage(unittest.TestCase):
    """Test cases for NotionPage class that require NOTION_TEST_PAGE_ID."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_page_id = os.getenv("NOTION_TEST_PAGE_ID")
        
        if not self.test_page_id:
            self.fail("NOTION_TEST_PAGE_ID environment variable not set")
    
    def test_add_content_and_clean(self):
        """
        Integration test: Add content to Notion page and verify cleaning works.
        
        This test:
        1. Adds paragraph content to the test page
        2. Verifies the content was added
        3. Cleans the page
        4. Verifies the content was removed
        """
        page = NotionPage(is_integration_test=True)
        
        # Step 1: Add test content to the page
        test_content = "This is a test paragraph for cleaning verification."
        try:
            response = page.client.blocks.children.append(
                block_id=self.test_page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": test_content}
                                }
                            ]
                        }
                    }
                ]
            )
            self.assertIsNotNone(response)
            print(f"✅ Added test content to page: {test_content}")
        except Exception as e:
            self.fail(f"Failed to add test content: {e}")
        
        # Step 2: Verify content was added
        try:
            blocks_response = page.client.blocks.children.list(block_id=self.test_page_id)
            blocks = blocks_response.get("results", [])
            self.assertGreater(len(blocks), 0, "No blocks found after adding content")
            
            # Look for our test content
            found_test_content = False
            for block in blocks:
                if block.get("type") == "paragraph":
                    rich_text = block.get("paragraph", {}).get("rich_text", [])
                    for text_obj in rich_text:
                        if text_obj.get("text", {}).get("content") == test_content:
                            found_test_content = True
                            break
                if found_test_content:
                    break
            
            self.assertTrue(found_test_content, "Test content not found in page blocks")
            print(f"✅ Verified test content exists on page (found {len(blocks)} blocks)")
        except Exception as e:
            self.fail(f"Failed to verify test content: {e}")
        
        # Step 3: Clean the page
        try:
            page.reset()
            print("✅ Page cleaning completed successfully")
        except Exception as e:
            self.fail(f"Page cleaning failed: {e}")
        
        # Step 4: Verify content was removed
        try:
            blocks_response = page.client.blocks.children.list(block_id=self.test_page_id)
            blocks = blocks_response.get("results", [])
            self.assertEqual(len(blocks), 0, f"Expected 0 blocks after cleaning, found {len(blocks)}")
            print("✅ Verified all content was removed from page")
        except Exception as e:
            self.fail(f"Failed to verify content removal: {e}")
    
    def test_clean_empty_page(self):
        """Test cleaning an already empty page."""
        page = NotionPage(is_integration_test=True)
        
        # First ensure the page is empty
        try:
            blocks_response = page.client.blocks.children.list(block_id=self.test_page_id)
            blocks = blocks_response.get("results", [])
            
            # If there are blocks, clean them first
            if blocks:
                for block in blocks:
                    page.client.blocks.delete(block_id=block["id"])
        except Exception as e:
            self.fail(f"Failed to prepare empty page: {e}")
        
        # Now test cleaning empty page
        try:
            page.reset()
            print("✅ Successfully cleaned empty page")
        except Exception as e:
            self.fail(f"Failed to clean empty page: {e}")
    
    def test_multiple_content_types_and_clean(self):
        """
        Test adding multiple types of content and verifying complete cleaning.
        
        This test adds different block types and verifies they are all removed.
        """
        page = NotionPage(is_integration_test=True)
        
        # Add multiple types of content
        try:
            # Add paragraph
            page.client.blocks.children.append(
                block_id=self.test_page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Test paragraph content"}
                                }
                            ]
                        }
                    }
                ]
            )
            
            # Add heading
            page.client.blocks.children.append(
                block_id=self.test_page_id,
                children=[
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Test Heading"}
                                }
                            ]
                        }
                    }
                ]
            )
            
            # Add bulleted list
            page.client.blocks.children.append(
                block_id=self.test_page_id,
                children=[
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Test list item"}
                                }
                            ]
                        }
                    }
                ]
            )
            
            print("✅ Added multiple content types to page")
        except Exception as e:
            self.fail(f"Failed to add multiple content types: {e}")
        
        # Verify content was added
        try:
            blocks_response = page.client.blocks.children.list(block_id=self.test_page_id)
            blocks = blocks_response.get("results", [])
            self.assertGreaterEqual(len(blocks), 3, "Should have at least 3 blocks")
            print(f"✅ Verified multiple content types exist ({len(blocks)} blocks)")
        except Exception as e:
            self.fail(f"Failed to verify multiple content types: {e}")
        
        # Clean the page
        try:
            page.reset()
            print("✅ Cleaned page with multiple content types")
        except Exception as e:
            self.fail(f"Failed to clean page with multiple content types: {e}")
        
        # Verify everything was removed
        try:
            blocks_response = page.client.blocks.children.list(block_id=self.test_page_id)
            blocks = blocks_response.get("results", [])
            self.assertEqual(len(blocks), 0, "All blocks should be removed after cleaning")
            print("✅ Verified all content types were removed")
        except Exception as e:
            self.fail(f"Failed to verify content removal: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2) 