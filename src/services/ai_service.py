"""
OpenAI service for AI-powered transcript processing.
"""

from typing import Dict, Any, List
from openai import OpenAI
from ..core.models import GeneratedIssue, GeneratedIssuesResponse
from ..core.config import Config


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def process_transcript(
        self, 
        system_prompt: str, 
        user_prompt: str
    ) -> List[GeneratedIssue]:
        """Process transcript and generate structured issues."""
        try:
            return self._call_openai_structured(system_prompt, user_prompt)
        except Exception as e:
            print(f"Error processing transcript with OpenAI: {e}")
            raise
    
    def _call_openai_structured(self, system_prompt: str, user_prompt: str) -> List[GeneratedIssue]:
        """Call OpenAI API with structured output using Pydantic models."""
        try:
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format=GeneratedIssuesResponse
            )
            
            # Get the parsed response
            parsed_response = response.choices[0].message.parsed
            return parsed_response.issues
            
        except Exception as e:
            print(f"Error calling OpenAI API with structured output: {e}")
            raise 