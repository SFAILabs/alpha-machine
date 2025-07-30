"""
Transcript filtering service for removing commercial/monetary content.
"""

import re
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from ...core.config import Config
from ...core.models import FilteredTranscript, TranscriptFilteringResult
from ...services.ai_service import OpenAIService
from ...services.supabase_service import SupabaseService
from ...core.utils import load_prompts


class TranscriptFilterService:
    """Service for filtering commercial/monetary content from transcripts."""
    
    def __init__(self):
        """Initialize the transcript filter service."""
        self.ai_service = OpenAIService()
        self.supabase_service = SupabaseService()
        self.prompts = load_prompts(Config.PROMPTS_FILE)
    
    def filter_transcript(self, transcript: str, filename: str = "unknown.txt") -> TranscriptFilteringResult:
        """
        Filter commercial/monetary content from a transcript using AI.
        
        Args:
            transcript: The original transcript text
            filename: Original filename for reference
            
        Returns:
            TranscriptFilteringResult with filtered content and metadata
        """
        start_time = time.time()
        
        try:
            # Load the filtering prompt
            prompt_config = self.prompts.get('filter_transcript_commercial_content')
            if not prompt_config:
                raise ValueError("Filtering prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            # Format the user prompt
            user_prompt = user_prompt_template.format(transcript=transcript)
            
            print(f"🔍 Filtering transcript: {filename}")
            print(f"   Original length: {len(transcript)} characters")
            
            # Call AI service to filter the transcript
            filtered_content = self.ai_service.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            if not filtered_content:
                raise ValueError("AI service returned empty filtered content")
            
            # Count redactions (simple heuristic)
            redaction_count = self._count_redactions(filtered_content)
            
            processing_time = time.time() - start_time
            
            print(f"   ✅ Filtering completed in {processing_time:.2f}s")
            print(f"   Filtered length: {len(filtered_content)} characters")
            print(f"   Redactions detected: {redaction_count}")
            
            return TranscriptFilteringResult(
                original_transcript=transcript,
                filtered_transcript=filtered_content,
                redaction_count=redaction_count,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"   ❌ Filtering failed: {e}")
            
            return TranscriptFilteringResult(
                original_transcript=transcript,
                filtered_transcript=transcript,  # Return original on failure
                redaction_count=0,
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    def _count_redactions(self, filtered_content: str) -> int:
        """Count the number of redaction placeholders in the filtered content."""
        redaction_patterns = [
            r'\[REDACTED_AMOUNT\]',
            r'\[COMMERCIAL_TERM\]',
            r'\[BUDGET_CONSTRAINT\]',
            r'\[PRICING_DISCUSSION\]',
            r'\[FINANCIAL_DISCUSSION\]',
            r'\[TIMELINE_CONSTRAINT\]'
        ]
        
        total_redactions = 0
        for pattern in redaction_patterns:
            matches = re.findall(pattern, filtered_content, re.IGNORECASE)
            total_redactions += len(matches)
        
        return total_redactions
    
    def extract_participants(self, transcript: str) -> List[str]:
        """Extract participant names from transcript."""
        # Simple regex to find email addresses and names
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        emails = re.findall(email_pattern, transcript)
        
        # Also look for names in format "Name | timestamp"
        name_pattern = r'^([^|]+)\s*\|\s*\d{2}:\d{2}'
        names = re.findall(name_pattern, transcript, re.MULTILINE)
        
        participants = list(set(emails + [name.strip() for name in names if name.strip()]))
        return participants
    
    def extract_project_tags(self, transcript: str) -> List[str]:
        """Extract project names/tags from transcript."""
        # Common project indicators
        project_indicators = [
            'Alpha Machine', 'Affirm Health', 'Vitality', 'RX Pharmacy', 
            'Rocket Takeoffs', 'My Data Move', 'Project X'
        ]
        
        found_projects = []
        for project in project_indicators:
            if project.lower() in transcript.lower():
                found_projects.append(project)
        
        return found_projects
    
    def store_filtered_transcript(self, 
                                filtered_result: TranscriptFilteringResult,
                                filename: str,
                                meeting_date: Optional[datetime] = None) -> Optional[str]:
        """
        Store filtered transcript in Supabase.
        
        Args:
            filtered_result: The filtering result
            filename: Original filename
            meeting_date: Optional meeting date
            
        Returns:
            Supabase record ID if successful, None otherwise
        """
        try:
            # Extract metadata
            participants = self.extract_participants(filtered_result.original_transcript)
            project_tags = self.extract_project_tags(filtered_result.original_transcript)
            
            # Create FilteredTranscript object
            filtered_transcript = FilteredTranscript(
                original_filename=filename,
                filtered_content=filtered_result.filtered_transcript,
                original_length=len(filtered_result.original_transcript),
                filtered_length=len(filtered_result.filtered_transcript),
                redaction_count=filtered_result.redaction_count,
                meeting_date=meeting_date or datetime.now(),
                participants=participants,
                project_tags=project_tags,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store in Supabase
            transcript_id = self.supabase_service.store_filtered_transcript(
                filtered_transcript.to_dict()
            )
            
            if transcript_id:
                print(f"   💾 Stored in Supabase with ID: {transcript_id}")
                return transcript_id
            else:
                print("   ❌ Failed to store in Supabase")
                return None
                
        except Exception as e:
            print(f"   ❌ Error storing filtered transcript: {e}")
            return None
    
    def process_and_store_transcript(self, 
                                   transcript: str, 
                                   filename: str,
                                   meeting_date: Optional[datetime] = None) -> Optional[str]:
        """
        Complete workflow: filter transcript and store in Supabase.
        
        Args:
            transcript: Original transcript text
            filename: Original filename
            meeting_date: Optional meeting date
            
        Returns:
            Supabase record ID if successful, None otherwise
        """
        print(f"🚀 Processing transcript: {filename}")
        
        # Step 1: Filter the transcript
        filtering_result = self.filter_transcript(transcript, filename)
        
        if not filtering_result.success:
            print(f"   ❌ Filtering failed: {filtering_result.error_message}")
            return None
        
        # Step 2: Store in Supabase
        transcript_id = self.store_filtered_transcript(
            filtering_result, filename, meeting_date
        )
        
        if transcript_id:
            print(f"   ✅ Complete workflow successful")
            return transcript_id
        else:
            print(f"   ❌ Storage failed")
            return None
    
    def get_filtered_transcript(self, transcript_id: str) -> Optional[FilteredTranscript]:
        """Retrieve filtered transcript from Supabase."""
        try:
            data = self.supabase_service.get_filtered_transcript(transcript_id)
            if data:
                return FilteredTranscript(
                    id=data.get('id'),
                    original_filename=data.get('original_filename'),
                    filtered_content=data.get('filtered_content'),
                    original_length=data.get('original_length'),
                    filtered_length=data.get('filtered_length'),
                    redaction_count=data.get('redaction_count'),
                    meeting_date=datetime.fromisoformat(data.get('meeting_date')) if data.get('meeting_date') else None,
                    participants=data.get('participants', []),
                    project_tags=data.get('project_tags', []),
                    created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None
                )
            return None
        except Exception as e:
            print(f"Error retrieving filtered transcript: {e}")
            return None 