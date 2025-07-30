"""
Notion service for Notion operations across all flows.
"""

from typing import Dict, Any, List, Optional
from notion_client import Client
from ..core.config import Config


class NotionService:
    """Service for Notion operations."""
    
    def __init__(self):
        """Initialize Notion client."""
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Notion client with configuration."""
        if Config.NOTION_TOKEN:
            self.client = Client(auth=Config.NOTION_TOKEN)
        else:
            print("Warning: Notion token not configured")
    
    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get page content by ID."""
        if not self.client:
            print("Error: Notion client not initialized")
            return None
        
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            return response
        except Exception as e:
            print(f"Error retrieving page: {e}")
            return None
    
    def get_database(self, database_id: str) -> Optional[Dict[str, Any]]:
        """Get database content by ID."""
        if not self.client:
            print("Error: Notion client not initialized")
            return None
        
        try:
            response = self.client.databases.query(database_id=database_id)
            return response
        except Exception as e:
            print(f"Error retrieving database: {e}")
            return None
    
    def search_pages(self, query: str) -> List[Dict[str, Any]]:
        """Search for pages with query."""
        if not self.client:
            print("Error: Notion client not initialized")
            return []
        
        try:
            response = self.client.search(query=query)
            return response.get("results", [])
        except Exception as e:
            print(f"Error searching pages: {e}")
            return []
    
    def get_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        """Get all blocks from a page."""
        if not self.client:
            print("Error: Notion client not initialized")
            return []
        
        try:
            response = self.client.blocks.children.list(block_id=page_id)
            return response.get("results", [])
        except Exception as e:
            print(f"Error retrieving page blocks: {e}")
            return []
    
    def create_page(self, parent_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new page."""
        if not self.client:
            print("Error: Notion client not initialized")
            return None
        
        try:
            response = self.client.pages.create(
                parent={"database_id": parent_id},
                properties=properties
            )
            return response
        except Exception as e:
            print(f"Error creating page: {e}")
            return None
    
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing page."""
        if not self.client:
            print("Error: Notion client not initialized")
            return None
        
        try:
            response = self.client.pages.update(page_id=page_id, properties=properties)
            return response
        except Exception as e:
            print(f"Error updating page: {e}")
            return None
    
    def get_project_info(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get project information from Notion."""
        if not self.client:
            print("Error: Notion client not initialized")
            return None
        
        try:
            # Search for project pages
            response = self.client.search(query=project_name)
            results = response.get("results", [])
            
            # Find the most relevant project page
            for result in results:
                if result.get("object") == "page":
                    properties = result.get("properties", {})
                    title_prop = properties.get("title", {})
                    if title_prop and project_name.lower() in title_prop.get("title", [{}])[0].get("plain_text", "").lower():
                        return result
            
            return None
        except Exception as e:
            print(f"Error getting project info: {e}")
            return None
    
    def get_client_documents(self, client_name: str) -> List[Dict[str, Any]]:
        """Get all documents related to a client."""
        if not self.client:
            print("Error: Notion client not initialized")
            return []
        
        try:
            response = self.client.search(query=client_name)
            results = response.get("results", [])
            
            # Filter for pages related to the client
            client_docs = []
            for result in results:
                if result.get("object") == "page":
                    properties = result.get("properties", {})
                    # Check if client name appears in any text property
                    for prop_name, prop_value in properties.items():
                        if prop_value.get("type") == "title":
                            title_text = prop_value.get("title", [{}])[0].get("plain_text", "")
                            if client_name.lower() in title_text.lower():
                                client_docs.append(result)
                                break
            
            return client_docs
        except Exception as e:
            print(f"Error getting client documents: {e}")
            return [] 