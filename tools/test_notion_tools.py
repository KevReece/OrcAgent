"""
Integration Tests for Notion Tools

Integration tests that require real Notion API access and fail if prerequisites are missing.
"""

import unittest
import os
from datetime import datetime
from tools.notion_tools import get_tools
from dotenv import load_dotenv
from tools.context import ToolsContext

load_dotenv(override=True)

def make_tools_context():
    return ToolsContext(
        role_repository=None,
        self_worker_name=None,
        agent_work_dir="/tmp",
        is_integration_test=True
    )

class TestNotionToolsIntegration(unittest.TestCase):
    """Integration tests for Notion tools that require real Notion API access."""


    def setUp(self):
        """Set up test environment."""
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["NOTION_API_KEY", "NOTION_TEST_PAGE_ID"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        self.notion_headers = {
            "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.notion_base_url = "https://api.notion.com/v1"

        # Create Notion tools instance - fail if initialization fails
        try:
            tools = get_tools(make_tools_context())

            class Self:
                def __init__(self, tools):
                    self.create_page = tools[0]
                    self.get_page = tools[1]
                    self.update_page_properties = tools[2]
                    self.append_paragraph_to_page = tools[3]
                    self.append_block_children = tools[4]
                    self.get_block_children = tools[5]
                    self.create_database = tools[6]
                    self.get_database = tools[7]
                    self.update_database_schema = tools[8]
                    self.query_database = tools[9]
                    self.get_page_content = tools[10]
                    self.search_pages = tools[11]
                    self.update_page_title = tools[12]
                    self.resolve_page_id = tools[13]

            self.notion_tools = Self(tools)            
        except Exception as e:
            self.fail(f"Failed to initialize NotionTools. This is a required prerequisite: {e}")
        
        # Create a test page for operations
        self.test_page_title = f"Test Page - {datetime.now()}"
        created_page = self.notion_tools.create_page(
            title=self.test_page_title,
            content="This is a test page for integration tests."
        )
        
        if not isinstance(created_page, dict) or "id" not in created_page:
            self.fail(f"Failed to create test page for integration tests: {created_page}")
        
        self.test_page_id = created_page["id"]

    def tearDown(self):
        """Clean up test page."""
        if hasattr(self, 'test_page_id') and self.test_page_id:
            # Archive the test page - ignore errors during cleanup
            try:
                import requests
                requests.patch(
                    f"{self.notion_base_url}/pages/{self.test_page_id}",
                    headers=self.notion_headers,
                    json={"archived": True}
                )
            except:
                pass

    def test_create_page_real_integration(self):
        """Test creating a page with real Notion API - integration test."""
        result = self.notion_tools.create_page(
            title="Integration Test Page",
            content="This is an integration test page."
        )
        
        self.assertIsInstance(result, dict, "Expected dict response for successful page creation")
        self.assertIn("id", result, "Expected 'id' field in successful page creation response")

    def test_update_page_title_real_integration(self):
        """Test updating page title with real Notion API - integration test."""
        new_title = f"Updated Integration Test Title - {datetime.now()}"
        result = self.notion_tools.update_page_title(
            page_id=self.test_page_id,
            new_title=new_title
        )
        
        self.assertIsInstance(result, str, "Expected string response for page title update")
        self.assertIn("Successfully updated page title", result, "Expected success message for page title update")
        self.assertIn(new_title, result, "Expected new title in success message")

    def test_append_paragraph_to_page_real_integration(self):
        """Test appending paragraph with real Notion API - integration test."""
        paragraph_content = f"Integration test paragraph content - {datetime.now()}"
        result = self.notion_tools.append_paragraph_to_page(
            page_id=self.test_page_id,
            paragraph=paragraph_content
        )
        
        self.assertIsInstance(result, dict, "Expected dict response for successful paragraph append")
        self.assertIn("results", result, "Expected 'results' field in successful append response")
        self.assertTrue(len(result["results"]) > 0, "Expected at least one result in append response")

    def test_get_page_content_real_integration(self):
        """Test getting page content with real Notion API - integration test."""
        result = self.notion_tools.get_page_content(self.test_page_id)
        
        self.assertIsInstance(result, str, "Expected string response for page content")
        self.assertIn("Page content:", result, "Expected page content prefix in response")
        self.assertIn(self.test_page_title, result, "Expected page title in content response")

    def test_search_pages_real_integration(self):
        """Test searching pages with real Notion API - integration test."""
        # Search for our test page
        result = self.notion_tools.search_pages("Integration Test")
        
        self.assertIsInstance(result, str, "Expected string response for search")
        self.assertTrue(
            result.startswith("Search results:") or result == "No pages found matching the search query",
            "Expected search results or no results message"
        )


class TestNotionToolsAPICallsIntegration(unittest.TestCase):
    """Integration tests for direct Notion API calls."""

    def setUp(self):
        """Set up test environment."""
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["NOTION_API_KEY", "NOTION_TEST_PAGE_ID"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        self.notion_headers = {
            "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.notion_base_url = "https://api.notion.com/v1"

        # Create Notion tools instance - fail if initialization fails
        try:
            tools = get_tools(make_tools_context())

            class Self:
                def __init__(self, tools):
                    self.create_page = tools[0]
                    self.get_page = tools[1]
                    self.update_page_properties = tools[2]
                    self.append_paragraph_to_page = tools[3]
                    self.append_block_children = tools[4]
                    self.get_block_children = tools[5]
                    self.create_database = tools[6]
                    self.get_database = tools[7]
                    self.update_database_schema = tools[8]
                    self.query_database = tools[9]
                    self.get_page_content = tools[10]
                    self.search_pages = tools[11]
                    self.update_page_title = tools[12]
                    self.resolve_page_id = tools[13]

            self.notion_tools = Self(tools)
        except Exception as e:
            self.fail(f"Failed to initialize NotionTools. This is a required prerequisite: {e}")

    def test_notion_api_authentication_integration(self):
        """Test Notion API authentication - integration test."""
        # Test authentication by making a simple API call
        try:
            import requests
            
            response = requests.get(
                f"{self.notion_base_url}/users/me",
                headers=self.notion_headers,
                timeout=10
            )
            
            # Should be authenticated successfully
            self.assertEqual(response.status_code, 200, "Expected successful authentication")
            response_data = response.json()
            self.assertIn("object", response_data, "Expected object field in authentication response")
            self.assertEqual(response_data["object"], "user", "Expected user object type")
        except Exception as e:
            self.fail(f"Notion API authentication test failed: {e}")

    def test_notion_database_access_integration(self):
        """Test Notion database access - integration test."""
        test_page_id = os.getenv("NOTION_TEST_PAGE_ID")
        if test_page_id:
            try:
                import requests
                
                response = requests.get(
                    f"{self.notion_base_url}/pages/{test_page_id}",
                    headers=self.notion_headers,
                    timeout=10
                )
                
                # Should successfully access the page
                self.assertEqual(response.status_code, 200, "Expected successful page access")
                response_data = response.json()
                self.assertIn("id", response_data, "Expected id field in page response")
                self.assertIn("properties", response_data, "Expected properties field in page response")
            except Exception as e:
                self.fail(f"Notion database access test failed: {e}")

    def test_notion_page_operations_real_integration(self):
        """Test complete Notion page operations - integration test."""
        # Create page
        create_result = self.notion_tools.create_page(
            title="Integration Test Complete Workflow",
            content="Testing complete workflow."
        )
        
        # Should get successful dict response
        self.assertIsInstance(create_result, dict, "Expected dict response for successful page creation")
        self.assertIn("id", create_result, "Expected id field in created page")
        
        created_page_id = create_result["id"]
        
        # Update title using the created page
        update_result = self.notion_tools.update_page_title(
            page_id=created_page_id,
            new_title="Updated Workflow Title"
        )
        
        # Should get successful string response
        self.assertIsInstance(update_result, str, "Expected string response for title update")
        self.assertIn("Successfully updated page title", update_result, "Expected success message")
        
        # Search for pages
        search_result = self.notion_tools.search_pages("Integration Test")
        
        # Should get successful search response
        self.assertIsInstance(search_result, str, "Expected string response for search")
        self.assertTrue(
            search_result.startswith("Search results:") or search_result == "No pages found matching the search query",
            "Expected search results or no results message"
        )
        
        # Clean up the created page
        try:
            import requests
            requests.patch(
                f"{self.notion_base_url}/pages/{created_page_id}",
                headers=self.notion_headers,
                json={"archived": True}
            )
        except:
            pass


class TestNotionToolsErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling with real Notion API."""

    def setUp(self):
        """Set up test environment."""
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["NOTION_API_KEY", "NOTION_TEST_PAGE_ID"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        # Create Notion tools instance - fail if initialization fails
        try:
            tools = get_tools(make_tools_context())

            class Self:
                def __init__(self, tools):
                    self.create_page = tools[0]
                    self.get_page = tools[1]
                    self.update_page_properties = tools[2]
                    self.append_paragraph_to_page = tools[3]
                    self.append_block_children = tools[4]
                    self.get_block_children = tools[5]
                    self.create_database = tools[6]
                    self.get_database = tools[7]
                    self.update_database_schema = tools[8]
                    self.query_database = tools[9]
                    self.get_page_content = tools[10]
                    self.search_pages = tools[11]
                    self.update_page_title = tools[12]
                    self.resolve_page_id = tools[13]

            self.notion_tools = Self(tools)
        except Exception as e:
            self.fail(f"Failed to initialize NotionTools. This is a required prerequisite: {e}")

    def test_notion_invalid_page_id_integration(self):
        """Test operations with invalid page ID - should fail with specific error."""
        result = self.notion_tools.get_page_content("invalid-page-id-12345")
        
        # Should fail with specific Notion API error message
        self.assertIsInstance(result, str, "Expected string error response")
        self.assertIn("Error", result, "Expected error message for invalid page ID")

    def test_notion_empty_search_query_integration(self):
        """Test search with empty query - should return specific error."""
        result = self.notion_tools.search_pages("")
        
        # Should return specific error for empty query
        self.assertIsInstance(result, str, "Expected string response for empty query")
        self.assertEqual(result, "Error: Search query cannot be empty", "Expected specific empty query error message")

    def test_notion_invalid_request_integration(self):
        """Test invalid API requests - should fail with specific error."""
        # Try to update non-existent page
        result = self.notion_tools.update_page_title(
            page_id="non-existent-page-123",
            new_title="This Should Fail"
        )
        
        # Should fail with specific API error
        self.assertIsInstance(result, str, "Expected string error response")
        self.assertIn("Error", result, "Expected error message for invalid page update")


class TestNotionToolsDirectAPIIntegration(unittest.TestCase):
    """Integration tests for direct Notion API operations."""

    def setUp(self):
        """Set up test environment with real Notion client."""
        # Ensure required environment variables are set - fail if missing
        required_env_vars = ["NOTION_API_KEY", "NOTION_TEST_PAGE_ID"]
        for var in required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set for integration tests")
        
        try:
            from notion_client import Client
            self.notion = Client(auth=os.getenv("NOTION_API_KEY"))
            self.parent_page_id = os.getenv("NOTION_TEST_PAGE_ID")
            tools = get_tools(make_tools_context())

            class Self:
                def __init__(self, tools):
                    self.create_page = tools[0]
                    self.get_page = tools[1]
                    self.update_page_properties = tools[2]
                    self.append_paragraph_to_page = tools[3]
                    self.append_block_children = tools[4]
                    self.get_block_children = tools[5]
                    self.create_database = tools[6]
                    self.get_database = tools[7]
                    self.update_database_schema = tools[8]
                    self.query_database = tools[9]
                    self.get_page_content = tools[10]
                    self.search_pages = tools[11]
                    self.update_page_title = tools[12]
                    self.resolve_page_id = tools[13]

            self.notion_tools = Self(tools)
            self.test_page_title = f"Test Page - {datetime.now()}"
            self.test_page_id = None
        except Exception as e:
            self.fail(f"Failed to initialize Notion client. This is a required prerequisite: {e}")

        # Create a test page for the tests
        created_page = self.notion_tools.create_page(
            title=self.test_page_title,
            parent_page_id=self.parent_page_id
        )
        # Handle potential string error from Notion client
        if not isinstance(created_page, dict):
            self.fail(f"Setup failed: Could not create test page. Response: {created_page}")

        self.assertIn("id", created_page)
        self.test_page_id = created_page["id"]

    def tearDown(self):
        """Archive the temporary test page."""
        if self.test_page_id:
            self.notion.pages.update(
                page_id=self.test_page_id,
                archived=True
            )

    def _find_content_in_rich_text(self, block, search_content):
        """Helper function to safely search for content in rich_text arrays."""
        rich_text = block.get("paragraph", {}).get("rich_text", [])
        for item in rich_text:
            text_content = item.get("text", {}).get("content", "")
            if search_content in text_content:
                return True
        return False

    def test_create_page(self):
        """Test creating a new page."""
        child_page_title = f"Test Child Page - {datetime.now()}"
        
        # Action
        result = self.notion_tools.create_page(
            title=child_page_title,
            parent_page_id=self.test_page_id
        )
        
        # Verification
        if not isinstance(result, dict):
            self.fail(f"API call failed during test. Response: {result}")
        self.assertIn("id", result)
        self.assertEqual(result.get("parent", {}).get("page_id", "").replace("-", ""), self.test_page_id.replace("-", ""))
        
        # Retrieve the page to confirm title
        page = self.notion.pages.retrieve(page_id=result["id"])
        title_text = page.get("properties", {}).get("title", {}).get("title", [{}])[0].get("text", {}).get("content")
        self.assertEqual(title_text, child_page_title)

    def test_append_paragraph_to_page(self):
        """Test appending a paragraph to a page."""
        content = f"This is a test paragraph added at {datetime.now()}."
        
        # Action
        result = self.notion_tools.append_paragraph_to_page(
            content=content,
            page_id=self.test_page_id
        )
        
        # Verification
        if not isinstance(result, dict):
            self.fail(f"API call failed during test. Response: {result}")
        self.assertIn("results", result)
        self.assertTrue(len(result["results"]) > 0)
        
        # Retrieve children to confirm content
        children = self.notion.blocks.children.list(block_id=self.test_page_id)
        self.assertTrue(any(
            self._find_content_in_rich_text(block, content)
            for block in children.get("results", [])
            if "paragraph" in block
        ))

    def test_create_page_with_env_var(self):
        """Test creating a page using the NOTION_PAGE_ID environment variable."""
        child_page_title = f"Test Child Page with Env Var - {datetime.now()}"
        
        # Action - Call without parent_page_id to test env var usage
        result = self.notion_tools.create_page(title=child_page_title)
        
        # Verification
        if not isinstance(result, dict):
            self.fail(f"API call failed during test. Response: {result}")
        self.assertIn("id", result)
        
        # The parent should be the env var NOTION_PAGE_ID
        expected_parent = self.parent_page_id.replace("-", "")
        actual_parent = result.get("parent", {}).get("page_id", "").replace("-", "")
        self.assertEqual(actual_parent, expected_parent)
        
        # Retrieve the page to confirm title
        page = self.notion.pages.retrieve(page_id=result["id"])
        title_text = page.get("properties", {}).get("title", {}).get("title", [{}])[0].get("text", {}).get("content")
        self.assertEqual(title_text, child_page_title)
        
        # Clean up the created page
        self.notion.pages.update(page_id=result["id"], archived=True)

    def test_append_paragraph_with_env_var(self):
        """Test appending a paragraph using the NOTION_PAGE_ID environment variable."""
        content = f"This is a test paragraph using env var - {datetime.now()}."
        
        # Action - Call without page_id to test env var usage
        result = self.notion_tools.append_paragraph_to_page(content=content)
        
        # Verification
        if not isinstance(result, dict):
            self.fail(f"API call failed during test. Response: {result}")
        self.assertIn("results", result)
        self.assertTrue(len(result["results"]) > 0)
        
        # Retrieve children from the env var page to confirm content
        children = self.notion.blocks.children.list(block_id=self.parent_page_id)
        self.assertTrue(any(
            self._find_content_in_rich_text(block, content)
            for block in children.get("results", [])
            if "paragraph" in block
        ))

    def test_append_paragraph_with_blank_page_id(self):
        """Test that blank page_id is treated as None and uses env var."""
        content = f"This is a test with blank page_id - {datetime.now()}."
        
        # Action - Call with empty string page_id to test blank handling
        result = self.notion_tools.append_paragraph_to_page(content=content, page_id="")
        
        # Verification
        if not isinstance(result, dict):
            self.fail(f"API call failed during test. Response: {result}")
        self.assertIn("results", result)
        self.assertTrue(len(result["results"]) > 0)
        
        # Retrieve children from the env var page to confirm content
        children = self.notion.blocks.children.list(block_id=self.parent_page_id)
        self.assertTrue(any(
            self._find_content_in_rich_text(block, content)
            for block in children.get("results", [])
            if "paragraph" in block
        ))

if __name__ == '__main__':
    unittest.main() 