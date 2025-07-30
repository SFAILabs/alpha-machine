"""
Notion flow processor for processing Notion information related to transcripts.
"""

from typing import Dict, Any, List
from ...services.notion_service import NotionService
from ...services.ai_service import OpenAIService
from ...core.config import Config


class NotionProcessor:
    """Processor for Notion information related to transcripts."""
    
    def __init__(self):
        """Initialize the Notion processor."""
        self.notion_service = NotionService()
        self.ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
    
    def process_project_documents(self, project_name: str) -> Dict[str, Any]:
        """Process Notion documents related to a project."""
        try:
            # Get project information from Notion
            project_info = self.notion_service.get_project_info(project_name)
            
            if not project_info:
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found in Notion"
                }
            
            # Extract relevant information
            project_data = self._extract_project_data(project_info)
            
            # Get related documents
            related_docs = self.notion_service.get_client_documents(project_name)
            
            return {
                "success": True,
                "project_data": project_data,
                "related_documents": related_docs,
                "project_name": project_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing project documents: {str(e)}"
            }
    
    def extract_requirements_from_page(self, page_id: str) -> Dict[str, Any]:
        """Extract requirements and specifications from a Notion page."""
        try:
            # Get page content
            page = self.notion_service.get_page(page_id)
            
            if not page:
                return {
                    "success": False,
                    "error": "Page not found"
                }
            
            # Get page blocks
            blocks = self.notion_service.get_page_blocks(page_id)
            
            # Extract text content
            text_content = self._extract_text_from_blocks(blocks)
            
            # Use AI to analyze requirements
            requirements = self._analyze_requirements(text_content)
            
            return {
                "success": True,
                "page_id": page_id,
                "requirements": requirements,
                "text_content": text_content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error extracting requirements: {str(e)}"
            }
    
    def get_client_context(self, client_name: str) -> Dict[str, Any]:
        """Get comprehensive client context from Notion."""
        try:
            # Get client documents
            client_docs = self.notion_service.get_client_documents(client_name)
            
            # Extract key information
            client_context = {
                "client_name": client_name,
                "documents": client_docs,
                "projects": [],
                "requirements": [],
                "timelines": []
            }
            
            # Process each document
            for doc in client_docs:
                doc_id = doc.get('id')
                if doc_id:
                    # Extract requirements from document
                    req_result = self.extract_requirements_from_page(doc_id)
                    if req_result['success']:
                        client_context['requirements'].append(req_result['requirements'])
            
            return {
                "success": True,
                "client_context": client_context
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting client context: {str(e)}"
            }
    
    def _extract_project_data(self, project_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant project data from Notion page."""
        properties = project_info.get('properties', {})
        
        project_data = {
            "id": project_info.get('id'),
            "title": "",
            "status": "",
            "timeline": "",
            "team": [],
            "description": ""
        }
        
        # Extract title
        title_prop = properties.get('title', {})
        if title_prop:
            title_text = title_prop.get('title', [{}])[0].get('plain_text', '')
            project_data['title'] = title_text
        
        # Extract other properties based on your Notion schema
        # This would need to be customized based on your actual Notion database structure
        
        return project_data
    
    def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract text content from Notion blocks."""
        text_content = ""
        
        for block in blocks:
            block_type = block.get('type')
            
            if block_type == 'paragraph':
                rich_text = block.get('paragraph', {}).get('rich_text', [])
                for text in rich_text:
                    text_content += text.get('plain_text', '') + "\n"
            
            elif block_type == 'heading_1':
                rich_text = block.get('heading_1', {}).get('rich_text', [])
                for text in rich_text:
                    text_content += "# " + text.get('plain_text', '') + "\n"
            
            elif block_type == 'heading_2':
                rich_text = block.get('heading_2', {}).get('rich_text', [])
                for text in rich_text:
                    text_content += "## " + text.get('plain_text', '') + "\n"
            
            elif block_type == 'bulleted_list_item':
                rich_text = block.get('bulleted_list_item', {}).get('rich_text', [])
                for text in rich_text:
                    text_content += "- " + text.get('plain_text', '') + "\n"
            
            elif block_type == 'numbered_list_item':
                rich_text = block.get('numbered_list_item', {}).get('rich_text', [])
                for text in rich_text:
                    text_content += "1. " + text.get('plain_text', '') + "\n"
        
        return text_content
    
    def _analyze_requirements(self, text_content: str) -> Dict[str, Any]:
        """Use AI to analyze requirements from text content."""
        system_prompt = """
        You are an expert at analyzing project requirements and specifications from documents.
        Extract and categorize the following information:
        1. Functional requirements
        2. Technical requirements
        3. Timeline and deadlines
        4. Stakeholders and responsibilities
        5. Constraints and dependencies
        """
        
        user_prompt = f"""
        Analyze this document content and extract requirements:
        
        {text_content}
        
        Return a structured analysis of the requirements.
        """
        
        try:
            response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            return {
                "ai_analysis": response,
                "raw_content": text_content
            }
        except Exception as e:
            return {
                "error": str(e),
                "raw_content": text_content
            } 