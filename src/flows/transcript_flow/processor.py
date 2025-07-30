"""
Transcript flow processor for AI filtering and Supabase upload.
"""

from typing import Dict, Any, List
from datetime import datetime
from ...services.ai_service import OpenAIService
from ...services.supabase_service import SupabaseService
from ...core.config import Config
from .filter_service import TranscriptFilterService


class TranscriptProcessor:
    """Processor for transcript filtering and storage."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        self.ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        self.supabase_manager = SupabaseService()
        self.filter_service = TranscriptFilterService()
    
    def process_transcript(self, raw_transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript with AI filtering and store in Supabase."""
        try:
            # AI filtering for commercial/monetary values
            filtered_data = self._filter_transcript(raw_transcript)
            
            # Prepare data for storage
            transcript_data = {
                "raw_transcript": raw_transcript,
                "filtered_data": filtered_data,
                "metadata": metadata,
                "created_at": datetime.now().isoformat(),
                "processed": True
            }
            
            # Store in Supabase
            transcript_id = self.supabase_manager.store_transcript(transcript_data)
            
            if transcript_id:
                return {
                    "success": True,
                    "transcript_id": transcript_id,
                    "filtered_data": filtered_data
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to store transcript in Supabase"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing transcript: {str(e)}"
            }
    
    def _filter_transcript(self, transcript: str) -> Dict[str, Any]:
        """Use AI to filter transcript for commercial/monetary values."""
        system_prompt = """
        You are an expert at analyzing meeting transcripts for commercial and monetary information.
        Extract and categorize the following information:
        1. Commercial values mentioned (dollar amounts, budgets, costs)
        2. Project timelines and deadlines
        3. Action items and tasks
        4. Key decisions made
        5. Stakeholders and responsibilities
        """
        
        user_prompt = f"""
        Analyze this transcript and extract commercial/monetary information:
        
        {transcript}
        
        Return a structured response with the extracted information.
        """
        
        try:
            # Use AI to filter the transcript
            response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            
            # For now, return the raw AI response
            # In the future, we could create a structured model for this
            return {
                "ai_analysis": response,
                "extraction_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error in AI filtering: {e}")
            return {
                "ai_analysis": None,
                "error": str(e),
                "extraction_timestamp": datetime.now().isoformat()
            }
    
    def get_transcript_summary(self, transcript_id: str) -> Dict[str, Any]:
        """Get a summary of a processed transcript."""
        transcript = self.supabase_manager.get_transcript(transcript_id)
        
        if not transcript:
            return {"error": "Transcript not found"}
        
        return {
            "transcript_id": transcript_id,
            "created_at": transcript.get("created_at"),
            "filtered_data": transcript.get("filtered_data"),
            "metadata": transcript.get("metadata")
        } 