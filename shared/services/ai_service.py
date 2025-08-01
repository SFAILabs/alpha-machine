"""
OpenAI service for AI-powered transcript processing.
"""

from typing import Dict, Any, List, Optional
from openai import OpenAI
from pydantic import BaseModel

from shared.core.models import GeneratedIssue, GeneratedIssuesResponse
from shared.core.config import Config


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self, api_key: str = None, model: str = None, max_tokens: int = None, temperature: float = None):
        self.client = OpenAI(api_key=api_key or Config.OPENAI_API_KEY)
        self.model = model or Config.OPENAI_MODEL
        self.max_tokens = max_tokens or Config.OPENAI_MAX_TOKENS
        self.temperature = temperature or Config.OPENAI_TEMPERATURE
    
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
        """Call OpenAI API with structured output using JSON schema."""
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
    
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error calling OpenAI API for text generation: {e}")
            raise 
    
    def get_structured_response(self, system_prompt: str, user_prompt: str, response_model: BaseModel) -> Dict[str, Any]:
        """Call OpenAI API and get a structured response based on a Pydantic model."""
        try:
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=response_model
            )
            return response.choices[0].message.parsed.model_dump()
        except Exception as e:
            print(f"Error calling OpenAI API for structured response: {e}")
            raise

    def chat_with_responses_api(self, user_input: str, previous_response_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat using OpenAI Responses API with conversation history.
        
        Args:
            user_input: The user's message (string or list of messages)
            previous_response_id: ID of the previous response (optional)
            
        Returns:
            Dict containing response text and response_id
        """
        try:
            # Prepare the request
            request_data = {
                "model": self.model,
                "input": user_input
            }
            
            # Add previous_response_id if provided
            if previous_response_id:
                request_data["previous_response_id"] = previous_response_id
            
            # Make the request using Responses API
            response = self.client.responses.create(**request_data)
            
            return {
                "response": response.output_text,
                "response_id": response.id,
                "usage": response.usage.model_dump() if response.usage else None
            }
            
        except Exception as e:
            print(f"Error in chat_with_responses_api: {e}")
            raise
    
    def continue_conversation(self, user_message: str, previous_response_id: str) -> Dict[str, Any]:
        """
        Continue an existing conversation using previous_response_id.
        
        Args:
            user_message: The user's message
            previous_response_id: ID of the previous response
            
        Returns:
            Dict containing response text and new response_id
        """
        return self.chat_with_responses_api(user_message, previous_response_id) 