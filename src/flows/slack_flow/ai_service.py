"""
AI service for Slack bot functions with context-aware prompting.
"""

import json
from typing import Dict, Any, Optional
from openai import OpenAI
from ...core.config import Config
from ...core.utils import load_prompts
from ...services.ai_service import OpenAIService


class SlackAIService:
    """AI service for Slack bot functions with context-aware prompting."""
    
    def __init__(self):
        """Initialize the Slack AI service."""
        self.openai_service = OpenAIService()
        self.prompts = load_prompts(Config.PROMPTS_FILE)
    
    def chat_with_context(self, user_message: str, context: Dict[str, Any], 
                         previous_response_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat with context using OpenAI Responses API.
        
        Args:
            user_message: The user's message
            context: Context data from ContextManager
            previous_response_id: Previous response ID for conversation history
            
        Returns:
            Dict containing response text and response_id
        """
        try:
            # Get chat prompt
            prompt_config = self.prompts.get('slack_bot_chat')
            if not prompt_config:
                raise ValueError("Chat prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            # Format user prompt with context
            formatted_user_prompt = user_prompt_template.format(
                context=json.dumps(context, indent=2),
                user_message=user_message
            )
            
            # Use Responses API for conversation history
            if previous_response_id:
                result = self.openai_service.continue_conversation(
                    formatted_user_prompt, previous_response_id
                )
            else:
                result = self.openai_service.chat_with_responses_api(formatted_user_prompt)
            
            return result
            
        except Exception as e:
            print(f"Error in chat_with_context: {e}")
            raise
    
    def summarize_meeting(self, context: Dict[str, Any]) -> str:
        """
        Generate meeting summary using context.
        
        Args:
            context: Context data from ContextManager
            
        Returns:
            Meeting summary text
        """
        try:
            prompt_config = self.prompts.get('slack_bot_summarize_meeting')
            if not prompt_config:
                raise ValueError("Meeting summary prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            # Get meeting transcript from context
            specific_meeting = context.get('specific_meeting')
            if not specific_meeting:
                return "No specific meeting found. Please provide a timestamp or meeting reference."
            
            meeting_transcript = specific_meeting.get('filtered_content', '')
            
            # Format user prompt
            formatted_user_prompt = user_prompt_template.format(
                context=json.dumps(context, indent=2),
                meeting_transcript=meeting_transcript
            )
            
            # Generate summary
            result = self.openai_service.generate_text(system_prompt, formatted_user_prompt)
            return result
            
        except Exception as e:
            print(f"Error in summarize_meeting: {e}")
            return f"Error generating meeting summary: {str(e)}"
    
    def generate_client_status(self, context: Dict[str, Any]) -> str:
        """
        Generate client status report using context.
        
        Args:
            context: Context data from ContextManager
            
        Returns:
            Client status report text
        """
        try:
            prompt_config = self.prompts.get('slack_bot_client_status')
            if not prompt_config:
                raise ValueError("Client status prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            client_name = context.get('client_name', 'Unknown Client')
            
            # Format user prompt
            formatted_user_prompt = user_prompt_template.format(
                context=json.dumps(context, indent=2),
                client_name=client_name
            )
            
            # Generate client status
            result = self.openai_service.generate_text(system_prompt, formatted_user_prompt)
            return result
            
        except Exception as e:
            print(f"Error in generate_client_status: {e}")
            return f"Error generating client status: {str(e)}"
    
    def create_ticket_suggestions(self, context: Dict[str, Any]) -> str:
        """
        Generate Linear ticket suggestions using context.
        
        Args:
            context: Context data from ContextManager
            
        Returns:
            Ticket suggestions text
        """
        try:
            prompt_config = self.prompts.get('slack_bot_create_tickets')
            if not prompt_config:
                raise ValueError("Create tickets prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            ticket_description = context.get('ticket_description', '')
            
            # Format user prompt
            formatted_user_prompt = user_prompt_template.format(
                context=json.dumps(context, indent=2),
                ticket_description=ticket_description
            )
            
            # Generate ticket suggestions
            result = self.openai_service.generate_text(system_prompt, formatted_user_prompt)
            return result
            
        except Exception as e:
            print(f"Error in create_ticket_suggestions: {e}")
            return f"Error generating ticket suggestions: {str(e)}"
    
    def get_teammember_info(self, context: Dict[str, Any]) -> str:
        """
        Generate team member information using context.
        
        Args:
            context: Context data from ContextManager
            
        Returns:
            Team member information text
        """
        try:
            prompt_config = self.prompts.get('slack_bot_teammember')
            if not prompt_config:
                raise ValueError("Team member prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            member_name = context.get('member_name', 'Unknown Member')
            
            # Format user prompt
            formatted_user_prompt = user_prompt_template.format(
                context=json.dumps(context, indent=2),
                member_name=member_name
            )
            
            # Generate team member info
            result = self.openai_service.generate_text(system_prompt, formatted_user_prompt)
            return result
            
        except Exception as e:
            print(f"Error in get_teammember_info: {e}")
            return f"Error generating team member info: {str(e)}"
    
    def generate_weekly_summary(self, context: Dict[str, Any]) -> str:
        """
        Generate weekly summary using context.
        
        Args:
            context: Context data from ContextManager
            
        Returns:
            Weekly summary text
        """
        try:
            prompt_config = self.prompts.get('slack_bot_weekly_summary')
            if not prompt_config:
                raise ValueError("Weekly summary prompt not found in prompts.yml")
            
            system_prompt = prompt_config['system_prompt']
            user_prompt_template = prompt_config['user_prompt']
            
            # Format user prompt
            formatted_user_prompt = user_prompt_template.format(
                context=json.dumps(context, indent=2)
            )
            
            # Generate weekly summary
            result = self.openai_service.generate_text(system_prompt, formatted_user_prompt)
            return result
            
        except Exception as e:
            print(f"Error in generate_weekly_summary: {e}")
            return f"Error generating weekly summary: {str(e)}" 