# notion_utils.py

import os
import json
import requests  # type: ignore
from typing import Optional, List, Callable
from logger.log_wrapper import get_logger
from tools.context import ToolsContext

# --- NotionClient Initialization ---

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


def get_tools(tools_context: ToolsContext):
    """Get Notion tools as a list of callables.
    
    Args:
        agent_work_dir: Working directory for tool operations (not used by Notion tools but required for interface consistency)
        is_integration_test: Whether this is running in integration test mode
    """
    def init(self, is_integration_test: bool = False):
        """Initialize NotionTools with optional integration test flag.
        
        Args:
            is_integration_test: If True, uses test environment variables
        """
        self.is_integration_test = is_integration_test
        self.logger = get_logger("tool:notion", __name__)
        
        # Use test environment variables if this is an integration test
        if is_integration_test:
            self.token = os.getenv("NOTION_API_KEY")
            self.database_id = os.getenv("NOTION_TEST_PAGE_ID")
        else:
            self.token = os.getenv("NOTION_API_KEY")
            self.database_id = os.getenv("NOTION_PAGE_ID")
            
        if not self.token:
            raise ValueError("NOTION_API_KEY environment variable is required")
            
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"
    
    self = type("Self", (), {})()
    init(self, tools_context.is_integration_test)

    MAX_RICH_TEXT_LEN = 2000

    def _chunk_text(text: str, max_len: int = MAX_RICH_TEXT_LEN - 50) -> List[str]:
        """Split text into chunks <= max_len, preferring newline boundaries.

        Notion enforces a 2000-char limit per rich_text item. We chunk slightly under
        that to remain safe with surrounding structure. We try to split on newlines; if
        a single line exceeds max_len, we hard-split.
        """
        if not text:
            return []
        chunks: List[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break
            # Try to split on the last newline within max_len
            split_at = remaining.rfind("\n", 0, max_len)
            if split_at == -1 or split_at < max_len // 2:
                # Hard split to avoid tiny chunks
                split_at = max_len
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip("\n")
        return chunks

    def _make_paragraph_blocks(text: str) -> List[dict]:
        """Create one or more paragraph blocks from text, chunking to satisfy limits."""
        blocks: List[dict] = []
        for chunk in _chunk_text(text):
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": chunk},
                            }
                        ]
                    },
                }
            )
        return blocks

    def _make_code_blocks(text: str, language: str = "plain_text") -> List[dict]:
        """Create one or more code blocks from text, chunking to satisfy limits."""
        blocks: List[dict] = []
        for chunk in _chunk_text(text):
            blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": chunk},
                            }
                        ],
                        "language": language,
                    },
                }
            )
        return blocks

    def notion_resolve_page_id(page_id: Optional[str] = None) -> str:
        """Resolves page_id, using environment variable if not provided."""
        if page_id is None or page_id == "":
            page_id = self.database_id
            if not page_id:
                return "Error: page_id not provided and NOTION_DATABASE_ID environment variable not set."
        return page_id
    
    def notion_create_page( title: str, content: Optional[str] = None, parent_page_id: Optional[str] = None):
        """Creates a new page in Notion."""
        # Use environment variable if parent_page_id is not provided
        if parent_page_id is None:
            parent_page_id = self.database_id
            if not parent_page_id:
                return "Error: parent_page_id not provided and NOTION_DATABASE_ID environment variable not set."
        
        try:
            title_list = [{"type": "text", "text": {"content": title}}]
            page_data = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": title_list
                    }
                }
            }
            
            # Add content as children if provided (chunked for Notion limits)
            if content:
                page_data["children"] = _make_paragraph_blocks(content)
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data
            )
            
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                return f"Error creating page: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error creating page: {e}"

    def notion_get_page( page_id: Optional[str] = None):
        """Retrieves a page from Notion."""
        # Resolve page_id, treating empty strings as None
        resolved_page_id = notion_resolve_page_id(page_id)
        if resolved_page_id.startswith("Error:"):
            return resolved_page_id
        
        try:
            response = requests.get(
                f"{self.base_url}/pages/{resolved_page_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error getting page: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error getting page: {e}"

    def notion_update_page_properties( properties: str, page_id: Optional[str] = None):
        """Updates page properties."""
        # Resolve page_id, treating empty strings as None
        resolved_page_id = notion_resolve_page_id(page_id)
        if resolved_page_id.startswith("Error:"):
            return resolved_page_id
        
        try:
            props_dict = json.loads(properties)
            
            response = requests.patch(
                f"{self.base_url}/pages/{resolved_page_id}",
                headers=self.headers,
                json={"properties": props_dict}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error updating page: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error updating page properties: {e}"

    def notion_append_paragraph_to_page( content: Optional[str] = None, page_id: Optional[str] = None, paragraph: Optional[str] = None):
        """Appends a paragraph to a page."""
        # Handle both 'content' and 'paragraph' parameters
        text_content = content if content is not None else paragraph
        if text_content is None:
            return "Error: Either 'content' or 'paragraph' parameter must be provided"
        
        resolved_page_id = notion_resolve_page_id(page_id)
        if resolved_page_id.startswith("Error:"):
            return resolved_page_id
        
        try:
            children_blocks = _make_paragraph_blocks(text_content)
            if not children_blocks:
                return "Error: Content is empty"

            response = requests.patch(
                f"{self.base_url}/blocks/{resolved_page_id}/children",
                headers=self.headers,
                json={"children": children_blocks}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error appending paragraph: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error appending paragraph: {e}"

    def notion_append_block_children( children: str) -> str:
        """Appends block children to the NOTION_DATABASE_ID."""
        try:
            page_id = self.database_id
            if not page_id:
                return "Error: NOTION_DATABASE_ID environment variable not set."
            
            # Format content appropriately, chunking to respect Notion limits
            is_code_like = any(
                keyword in children for keyword in [
                    "FROM ", "COPY ", "import ", "def ", "function", "<?", "<html", "<div"
                ]
            )
            if is_code_like:
                formatted_children = _make_code_blocks(children, language="plain_text")
            else:
                formatted_children = _make_paragraph_blocks(children)
            
            # Make the API call with properly formatted data
            response = requests.patch(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self.headers,
                json={"children": formatted_children}
            )
            
            if response.status_code == 200:
                return "Successfully appended content to page"
            else:
                return f"Error appending to Notion: {response.status_code} - {response.text}"
                
        except json.JSONDecodeError as e:
            return f"Error formatting content for Notion API: {e}"
        except Exception as e:
            return f"Error appending block children: {e}"

    def notion_get_block_children( block_id: Optional[str] = None):
        """Retrieves the children of a specific block or page."""
        # Resolve block_id, treating empty strings as None
        resolved_block_id = notion_resolve_page_id(block_id)
        if resolved_block_id.startswith("Error:"):
            return resolved_block_id
        
        try:
            response = requests.get(
                f"{self.base_url}/blocks/{resolved_block_id}/children",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error getting block children: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error getting block children: {e}"

    def notion_create_database( title: str, properties: str, parent_page_id: Optional[str] = None):
        """Creates a new database within a parent page."""
        # Use environment variable if parent_page_id is not provided
        if parent_page_id is None:
            parent_page_id = self.database_id
            if not parent_page_id:
                return "Error: parent_page_id not provided and NOTION_DATABASE_ID environment variable not set."
        
        try:
            props_dict = json.loads(properties)
            title_list = [{"type": "text", "text": {"content": title}}]
            
            database_data = {
                "parent": {"page_id": parent_page_id},
                "title": title_list,
                "properties": props_dict
            }
            
            response = requests.post(
                f"{self.base_url}/databases",
                headers=self.headers,
                json=database_data
            )
            
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                return f"Error creating database: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error creating database: {e}"

    def notion_get_database( database_id: str):
        """Retrieves a database by its ID."""
        try:
            response = requests.get(
                f"{self.base_url}/databases/{database_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error getting database: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error getting database: {e}"

    def notion_update_database_schema( database_id: str, properties: str):
        """Updates the schema of a database."""
        try:
            props_dict = json.loads(properties)
            
            response = requests.patch(
                f"{self.base_url}/databases/{database_id}",
                headers=self.headers,
                json={"properties": props_dict}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error updating database: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error updating database schema: {e}"

    def notion_query_database( database_id: str, filter: Optional[str] = None):
        """Queries a database."""
        try:
            query_data = {}
            if filter:
                query_data["filter"] = json.loads(filter)
            
            response = requests.post(
                f"{self.base_url}/databases/{database_id}/query",
                headers=self.headers,
                json=query_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error querying database: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error querying database: {e}"

    def notion_get_page_content( page_id: Optional[str] = None) -> str:
        """Gets page content including blocks."""
        resolved_page_id = notion_resolve_page_id(page_id)
        if resolved_page_id.startswith("Error:"):
            return resolved_page_id
        
        try:
            # Get page details
            page_response = notion_get_page(resolved_page_id)
            if isinstance(page_response, str) and page_response.startswith("Error"):
                return page_response
            
            # Get page blocks
            blocks_response = notion_get_block_children(resolved_page_id)
            if isinstance(blocks_response, str) and blocks_response.startswith("Error"):
                return f"Page found but error getting content: {blocks_response}"
            
            # Format response
            page_title = "Unknown"
            if isinstance(page_response, dict):
                properties = page_response.get("properties", {})
                title_prop = properties.get("title", {})
                if "title" in title_prop and title_prop["title"]:
                    page_title = title_prop["title"][0].get("text", {}).get("content", "Unknown")
            
            content_summary = f"Page content: '{page_title}'"
            if isinstance(blocks_response, dict) and "results" in blocks_response:
                content_summary += f" (contains {len(blocks_response['results'])} blocks)"
            
            return content_summary
            
        except Exception as e:
            return f"Error getting page content: {e}"

    def notion_search_pages( query: str) -> str:
        """Searches for pages by title."""
        try:
            if not query or query.strip() == "":
                return "Error: Search query cannot be empty"
            
            search_data = {
                "query": query,
                "filter": {
                    "value": "page",
                    "property": "object"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=search_data
            )
            
            if response.status_code == 200:
                results = response.json()
                if "results" in results and len(results["results"]) > 0:
                    pages = []
                    for page in results["results"]:
                        title = "Untitled"
                        if "properties" in page and "title" in page["properties"]:
                            title_prop = page["properties"]["title"]
                            if "title" in title_prop and title_prop["title"]:
                                title = title_prop["title"][0].get("text", {}).get("content", "Untitled")
                        pages.append(f"- {title} ({page['id']})")
                    
                    return f"Search results:\n" + "\n".join(pages)
                else:
                    return "No pages found matching the search query"
            else:
                return f"Error searching pages: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error searching pages: {e}"

    def notion_update_page_title( page_id: str, new_title: str) -> str:
        """Updates a page title."""
        try:
            update_data = {
                "properties": {
                    "title": {
                        "title": [
                            {
                                "type": "text",
                                "text": {
                                    "content": new_title
                                }
                            }
                        ]
                    }
                }
            }
            
            response = requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json=update_data
            )
            
            if response.status_code == 200:
                return f"Successfully updated page title to '{new_title}'"
            else:
                return f"Error updating page title: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error updating page title: {e}"
    
    # Return list of tools
    return [
        notion_create_page,
        notion_get_page,
        notion_update_page_properties,
        notion_append_paragraph_to_page,
        notion_append_block_children,
        notion_get_block_children,
        notion_create_database,
        notion_get_database,
        notion_update_database_schema,
        notion_query_database,
        notion_get_page_content,
        notion_search_pages,
        notion_update_page_title,
        notion_resolve_page_id,
    ]