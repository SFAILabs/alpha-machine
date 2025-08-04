"""
Transcript flow processor for AI filtering and Supabase upload.
"""

from typing import Dict, Any, List
from datetime import datetime, date
from fastapi import APIRouter
from pydantic import BaseModel, Field
import yaml

from shared.core.config import Config
from shared.services.ai_service import OpenAIService
from shared.services.linear_service import LinearService
from shared.core.models import GeneratedIssuesResponse

class TranscriptRequest(BaseModel):
    raw_transcript: str
    metadata: Dict[str, Any]

class TranscriptProcessor:
    """Processes a raw transcript to extract structured Linear issues."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        self.ai_service = OpenAIService()
        self.linear_service = LinearService(
            api_key=Config.LINEAR_API_KEY,
            team_name=Config.LINEAR_TEAM_NAME,
            default_assignee=None # No longer needed
        )
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from YAML file."""
        with open(Config.PROMPTS_FILE, 'r') as f:
            return yaml.safe_load(f)
    
    def process_transcript(self, raw_transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript to generate Linear issues."""
        try:
            # Fetch the current Linear context
            linear_context = self.linear_service.get_workspace_context()
            linear_context_str = linear_context.format_for_prompt()

            # Format the prompt
            prompt_config = self.prompts['transcript_to_linear_tickets']
            system_prompt = prompt_config['system_prompt']
            user_prompt = prompt_config['user_prompt'].format(
                linear_context=linear_context_str,
                transcription=raw_transcript,
                today_date=date.today().isoformat()
            )

            # Call the AI service to get structured data
            generated_issues = self.ai_service.get_structured_response(
                system_prompt, user_prompt, GeneratedIssuesResponse
            )

            return generated_issues
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing transcript: {str(e)}"
            }

processor_router = APIRouter()
processor = TranscriptProcessor()

@processor_router.post("/process")
def process_transcript_endpoint(request: TranscriptRequest):
    return processor.process_transcript(request.raw_transcript, request.metadata) 