"""
Notion Page Management Module

This module provides functionality to clean and reset a Notion page
by removing all blocks and content.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
import notion_client
from dotenv import load_dotenv
from logger.log_wrapper import get_logger

load_dotenv(override=True)


class NotionPageAgentEnvironment:
    """Notion page management class with cleaning capabilities."""
    
    def __init__(self, is_integration_test: bool = False):
        """
        Initialize Notion page manager.
        
        Args:
            is_integration_test: Whether to use test page configuration
        """
        self.page_id, self.api_key = self._get_page_config(is_integration_test)
        self.client = notion_client.Client(auth=self.api_key)
        self.logger = get_logger("env:notion", __name__)
    
    def _get_page_config(self, is_integration_test: bool = False) -> tuple[str, str]:
        """
        Get page configuration from environment variables.
        
        Args:
            is_integration_test: Whether to use test page configuration
        
        Returns:
            tuple: (page_id, api_key)
            
        Raises:
            ValueError: If required environment variables are not set
        """
        if is_integration_test:
            page_id = os.getenv("NOTION_TEST_PAGE_ID")
        else:
            page_id = os.getenv("NOTION_PAGE_ID")
        
        api_key = os.getenv("NOTION_API_KEY")
        
        if not page_id:
            if is_integration_test:
                raise ValueError("NOTION_TEST_PAGE_ID environment variable is required for integration tests")
            else:
                raise ValueError("NOTION_PAGE_ID environment variable is required")
        if not api_key:
            raise ValueError("NOTION_API_KEY environment variable is required")
        
        return page_id, api_key
    
    def reset(self) -> None:
        """
        Clean the Notion page by removing all content blocks.
        
        Raises:
            Exception: If cleaning fails
        """
        self.logger.info(f"Starting cleanup of Notion page: {self.page_id}")
        
        # Remove all blocks
        if not self._remove_all_blocks():
            raise Exception("Failed to remove all blocks")
        
        self.logger.info(f"Notion page {self.page_id} cleaned successfully!")
    
    def _remove_all_blocks(self) -> bool:
        """
        Remove all blocks from the Notion page using controlled parallel deletion.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.page_id:
                self.logger.error("No page ID available")
                return False
                
            # Get all blocks from the page
            response = self.client.blocks.children.list(block_id=self.page_id)
            if hasattr(response, 'get'):
                blocks = response.get("results", [])
            else:
                blocks = getattr(response, "results", [])
            
            if not blocks:
                self.logger.info("No blocks found to remove")
                return True
            
            # Delete blocks with controlled concurrency
            deleted_count = asyncio.run(self._delete_blocks_controlled(blocks))
            
            self.logger.info(f"Successfully deleted {deleted_count} blocks from {len(blocks)} total blocks")
            return deleted_count > 0 or len(blocks) == 0
            
        except Exception as e:
            self.logger.error(f"Error removing blocks: {e}")
            return False
    
    async def _delete_blocks_controlled(self, blocks: list) -> int:
        """
        Delete blocks with controlled concurrency to avoid rate limits.
        
        Args:
            blocks: List of block objects to delete
            
        Returns:
            int: Number of successfully deleted blocks
        """
        deleted_count = 0
        max_workers = 3  # Limit concurrent requests to avoid rate limits
        semaphore = asyncio.Semaphore(max_workers)
        
        async def delete_block_with_retry(block: dict) -> bool:
            async with semaphore:
                return await self._delete_single_block_with_retries(block)
        
        # Process blocks in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            tasks = [delete_block_with_retry(block) for block in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, bool) and result:
                    deleted_count += 1
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < len(blocks):
                await asyncio.sleep(0.5)
        
        return deleted_count
    
    async def _delete_single_block_with_retries(self, block: dict) -> bool:
        """
        Delete a single block with up to three retry attempts.
        
        Args:
            block: Block object to delete
            
        Returns:
            bool: True if deletion succeeded, False otherwise
        """
        max_attempts = 5
        base_delay = 0.5
        
        for attempt in range(max_attempts):
            try:
                # Use ThreadPoolExecutor to run the synchronous Notion client call
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    await loop.run_in_executor(
                        executor, 
                        self.client.blocks.delete, 
                        block["id"]
                    )
                return True
                
            except Exception as e:
                error_msg = str(e)
                is_conflict_error = "Conflict occurred while saving" in error_msg
                
                if attempt < max_attempts - 1 and is_conflict_error:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Attempt {attempt + 1} failed for block {block['id']}: {error_msg}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Failed to delete block {block['id']} after {attempt + 1} attempts: {error_msg}")
                    return False
        
        return False


if __name__ == "__main__":
    # This allows the module to be run standalone for testing
    page = NotionPageAgentEnvironment()
    page.reset() 