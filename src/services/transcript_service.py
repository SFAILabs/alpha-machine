"""
Transcript service for loading and managing meeting transcripts.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Tuple
from ..core.config import Config


class TranscriptService:
    """Service for managing transcript data and prompts."""
    
    def __init__(self, prompts_file: Path = None, transcript_file: Path = None):
        self.prompts_file = prompts_file or Config.PROMPTS_FILE
        self.transcript_file = transcript_file or Config.TRANSCRIPT_FILE
    
    def load_prompts(self) -> Dict[str, Any]:
        """Load prompts from YAML file."""
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompts file not found: {self.prompts_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing prompts file: {e}")
    
    def load_transcript(self) -> str:
        """Load transcript from text file."""
        try:
            with open(self.transcript_file, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Transcript file not found: {self.transcript_file}")
        except Exception as e:
            raise ValueError(f"Error reading transcript file: {e}")
    
    def format_prompts(
        self, 
        transcript: str, 
        linear_context: str
    ) -> Tuple[str, str]:
        """Format the system and user prompts with transcript and Linear context."""
        from datetime import datetime
        
        prompts = self.load_prompts()
        prompt_config = prompts.get('transcript_to_linear_tickets', {})
        
        system_prompt = prompt_config.get('system_prompt', '')
        user_prompt_template = prompt_config.get('user_prompt', '')
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Format the user prompt with the transcript, Linear context, and today's date
        user_prompt = user_prompt_template.format(
            linear_context=linear_context,
            transcription=transcript,
            today_date=today
        )
        
        return system_prompt, user_prompt
    
    def validate_files(self) -> bool:
        """Validate that required files exist."""
        if not self.prompts_file.exists():
            print(f"Warning: Prompts file not found: {self.prompts_file}")
            return False
        
        if not self.transcript_file.exists():
            print(f"Warning: Transcript file not found: {self.transcript_file}")
            return False
        
        return True 