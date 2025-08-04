"""
Slack Command Handler for Alpha Machine Bot

Simplified handler that uses prompts.yml and Slack's native history.
"""

import json
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta

from shared.core.config import Config
from shared.core.utils import load_prompts
from shared.services.slack_service import SlackService
from shared.services.ai_service import OpenAIService
from shared.services.linear_service import LinearService
from shared.services.notion_service import NotionService
from shared.services.supabase_service import SupabaseService


class SlackCommandHandler:
    """
    Handles processing of Slack slash commands using prompts.yml.
    
    PRODUCTION SAFETY:
    - Uses a single Linear service instance.
    - Write operations are only enabled if LINEAR_TEST_MODE is true.
    - This prevents accidental writes to the production Linear workspace.
    """
    
    def __init__(self):
        """Initialize all required services."""
        self.slack_service = SlackService()
        self.ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        self.linear_service = LinearService(
            api_key=Config.LINEAR_API_KEY,
            team_name=Config.LINEAR_TEAM_NAME,
        )
        self.notion_service = NotionService()
        self.supabase_service = SupabaseService()
        self.prompts = load_prompts(Config.PROMPTS_FILE)
    
    async def handle_command(self, payload: Dict[str, Any]) -> None:
        """Route command to appropriate handler."""
        command = payload.get("command", "")
        response_url = payload.get("response_url", "")
        
        try:
            if command == "/chat":
                response = await self._handle_chat_command(payload)
            elif command == "/summarize":
                response = await self._handle_summarize_command(payload)
            elif command == "/create-ticket" or command == "/create":
                response = await self._handle_create_ticket_command(payload)
            elif command == "/update":
                response = await self._handle_update_ticket_command(payload)
            elif command == "/teammember":
                response = await self._handle_teammember_command(payload)
            elif command == "/weekly-summary":
                response = await self._handle_weekly_summary_command(payload)
            else:
                response = {
                    "response_type": "ephemeral",
                    "text": f"Unknown command: {command}"
                }
            
            await self._send_response(response_url, response)
            
        except Exception as e:
            error_response = {
                "response_type": "ephemeral",
                "text": f"❌ Error processing {command}: {str(e)}"
            }
            await self._send_response(response_url, error_response)
    
    async def _handle_chat_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /chat command using prompts.yml and Slack history."""
        text = payload.get("text", "").strip()
        channel_id = payload.get("channel_id", "")
        user_id = payload.get("user_id", "")
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please provide a question or message to chat about."
            }
        
        # Get context and recent Slack history
        context = await self._get_comprehensive_context()
        slack_history = self._get_recent_slack_history(channel_id, user_id)
        
        # Use prompts.yml
        prompt_config = self.prompts.get('slack_bot_chat')
        if not prompt_config:
            return {
                "response_type": "ephemeral",
                "text": "❌ Chat prompt configuration not found."
            }
        
        system_prompt = prompt_config['system_prompt']
        user_prompt = prompt_config['user_prompt'].format(
            context=f"{context}\n\nRecent Slack History:\n{slack_history}",
            user_message=text
        )
        
        try:
            response_text = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            response_text = response_text[0] if response_text else "I couldn't generate a response at this time."
        except Exception as e:
            response_text = f"Error generating AI response: {str(e)}"
        
        return {
            "response_type": "ephemeral",
            "text": f"🤖 **AI Response:**\n\n{response_text}"
        }
    
    async def _handle_summarize_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /summarize command using prompts.yml."""
        text = payload.get("text", "").strip()
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please specify what to summarize:\n• `/summarize last @meeting @timestamp`\n• `/summarize client [client_name]`"
            }
        
        args = text.split()
        
        if len(args) >= 2 and args[0] == "last":
            return await self._handle_meeting_summary(args[1:])
        elif "client" in text.lower():
            return await self._handle_client_summary(text)
        else:
            return {
                "response_type": "ephemeral",
                "text": "❌ Invalid format. Use:\n• `/summarize last @meeting @timestamp`\n• `/summarize client [client_name]`"
            }
    
    async def _handle_create_ticket_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /create-ticket command.
        
        In test mode, this command creates a ticket in Linear.
        Otherwise, it provides an AI analysis of what ticket should be created.
        """
        text = payload.get("text", "").strip()
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please describe what you want to create in Linear."
            }
        
        context = await self._get_comprehensive_context()
        
        prompt_config = self.prompts.get('slack_bot_create_tickets')
        if not prompt_config:
            return {
                "response_type": "ephemeral",
                "text": "❌ Create tickets prompt configuration not found."
            }
        
        system_prompt = prompt_config['system_prompt']
        user_prompt = prompt_config['user_prompt'].format(
            context=context,
            ticket_description=text
        )
        
        try:
            ai_response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            
            # If not in test mode, return the analysis
            if not Config.LINEAR_TEST_MODE:
                return {
                    "response_type": "ephemeral",
                    "text": f"📋 **Linear Ticket Analysis (Test Mode Disabled):**\n\n{ai_response[0]}"
                }
            
            # In test mode, create the ticket
            issue_data = json.loads(ai_response[0])
            created_issue = self.linear_service.create_issue(issue_data)
            
            if created_issue:
                return {
                    "response_type": "in_channel",
                    "text": f"✅ **Ticket Created in Linear:**\n\n**Title:** {created_issue['title']}\n**ID:** {created_issue['id']}"
                }
            else:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ **Failed to create Linear ticket.** The AI analysis was:\n\n" + ai_response[0]
                }
                
        except json.JSONDecodeError:
            return {
                "response_type": "ephemeral",
                "text": f"❌ **Error:** The AI returned an invalid format. Analysis:\n\n{ai_response[0]}"
            }
        except Exception as e:
            return {
                "response_type": "ephemeral", 
                "text": f"❌ Error processing ticket creation: {str(e)}"
            }
    
    async def _handle_update_ticket_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /update command for updating existing Linear tickets.
        
        In test mode, this command updates a ticket in Linear.
        Otherwise, it provides an AI analysis of what should be updated.
        """
        text = payload.get("text", "").strip()
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please describe what you want to update in Linear.\n\nExamples:\n• `/update ticket ABC-123 to in progress`\n• `/update ABC-123: change title to 'New Task Name'`\n• `/update mark ticket XYZ-456 as completed`"
            }
        
        context = await self._get_comprehensive_context()
        
        prompt_config = self.prompts.get('slack_bot_update_tickets')
        if not prompt_config:
            return {
                "response_type": "ephemeral",
                "text": "❌ Update tickets prompt configuration not found."
            }
        
        system_prompt = prompt_config['system_prompt']
        user_prompt = prompt_config['user_prompt'].format(
            context=context,
            update_request=text
        )
        
        try:
            ai_response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            
            # If not in test mode, return the analysis
            if not Config.LINEAR_TEST_MODE:
                return {
                    "response_type": "ephemeral",
                    "text": f"📝 **Linear Ticket Update Analysis (Test Mode Disabled):**\n\n{ai_response[0]}"
                }
            
            # In test mode, parse the AI response and update the ticket
            update_data = json.loads(ai_response[0])
            ticket_id = update_data.get('ticket_id')
            updates = update_data.get('updates', {})
            summary = update_data.get('summary', 'Ticket update')
            
            if not ticket_id or not updates:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ **Unable to parse update request.** Please be more specific about which ticket to update and what changes to make."
                }
            
            # Update the ticket
            updated_issue = self.linear_service.update_issue(ticket_id, updates)
            
            if updated_issue:
                return {
                    "response_type": "in_channel",
                    "text": f"✅ **Ticket Updated in Linear:**\n\n**Ticket:** {ticket_id}\n**Summary:** {summary}\n**URL:** {updated_issue.get('url', 'N/A')}"
                }
            else:
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ **Failed to update Linear ticket.** The AI analysis was:\n\n{ai_response[0]}"
                }
                
        except json.JSONDecodeError:
            return {
                "response_type": "ephemeral",
                "text": f"❌ **Error:** The AI returned an invalid format. Analysis:\n\n{ai_response[0]}"
            }
        except Exception as e:
            return {
                "response_type": "ephemeral", 
                "text": f"❌ Error processing ticket update: {str(e)}"
            }
    
    async def _handle_teammember_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /teammember command using prompts.yml."""
        text = payload.get("text", "").strip()
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please specify a team member name or @username."
            }
        
        context = await self._get_comprehensive_context()
        
        prompt_config = self.prompts.get('slack_bot_teammember')
        if not prompt_config:
            return {
                "response_type": "ephemeral",
                "text": "❌ Team member prompt configuration not found."
            }
        
        system_prompt = prompt_config['system_prompt']
        user_prompt = prompt_config['user_prompt'].format(
            context=context,
            member_name=text
        )
        
        try:
            ai_response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            ai_response = ai_response[0] if ai_response else "No information found for this team member."
            
            return {
                "response_type": "ephemeral",
                "text": f"👤 **Team Member Info:**\n\n{ai_response}"
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral", 
                "text": f"❌ Error getting team member info: {str(e)}"
            }
    
    async def _handle_weekly_summary_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /weekly-summary command using prompts.yml."""
        context = await self._get_comprehensive_context()
        
        prompt_config = self.prompts.get('slack_bot_weekly_summary')
        if not prompt_config:
            return {
                "response_type": "ephemeral",
                "text": "❌ Weekly summary prompt configuration not found."
            }
        
        system_prompt = prompt_config['system_prompt']
        user_prompt = prompt_config['user_prompt'].format(context=context)
        
        try:
            ai_response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            ai_response = ai_response[0] if ai_response else "Unable to generate weekly summary."
            
            return {
                "response_type": "in_channel",
                "text": ai_response
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error generating weekly summary: {str(e)}"
            }
    
    async def _handle_meeting_summary(self, args: List[str]) -> Dict[str, Any]:
        """Handle meeting summary using prompts.yml."""
        try:
            end_date = datetime.now().isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            transcripts = self.supabase_service.get_transcripts_by_date_range(start_date, end_date)
            
            if not transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "📭 No recent meetings found in the last 7 days."
                }
            
            recent_meeting = transcripts[0]
            meeting_date = recent_meeting.get('metadata', {}).get('meeting_date', 'Unknown date')
            raw_transcript = recent_meeting.get('raw_transcript', '')
            
            if not raw_transcript:
                return {
                    "response_type": "ephemeral", 
                    "text": "📭 No transcript content found for recent meeting."
                }
            
            prompt_config = self.prompts.get('slack_bot_summarize_meeting')
            if not prompt_config:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ Meeting summary prompt configuration not found."
                }
            
            system_prompt = prompt_config['system_prompt']
            user_prompt = prompt_config['user_prompt'].format(
                context=f"Meeting Date: {meeting_date}",
                meeting_transcript=raw_transcript[:3000]
            )
            
            summary = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            summary = summary[0] if summary else "Unable to generate meeting summary."
            
            return {
                "response_type": "ephemeral",
                "text": f"📅 **Meeting Summary - {meeting_date}**\n\n{summary}"
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error generating meeting summary: {str(e)}"
            }
    
    async def _handle_client_summary(self, text: str) -> Dict[str, Any]:
        """Handle client status summary using prompts.yml."""
        try:
            client_name = text.replace("client", "").strip()
            
            if not client_name:
                return {
                    "response_type": "ephemeral",
                    "text": "Please specify a client name: `/summarize client [client_name]`"
                }
            
            context = await self._get_comprehensive_context()
            
            prompt_config = self.prompts.get('slack_bot_client_status')
            if not prompt_config:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ Client status prompt configuration not found."
                }
            
            system_prompt = prompt_config['system_prompt']
            user_prompt = prompt_config['user_prompt'].format(
                context=context,
                client_name=client_name
            )
            
            summary = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            summary = summary[0] if summary else f"No information found for client: {client_name}"
            
            return {
                "response_type": "ephemeral",
                "text": f"📊 **Client Status: {client_name.title()}**\n\n{summary}"
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error generating client summary: {str(e)}"
            }
    
    async def _get_comprehensive_context(self) -> str:
        """Get comprehensive context from all sources."""
        context_parts = []
        
        try:
            # Recent transcripts
            end_date = datetime.now().isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            transcripts = self.supabase_service.get_transcripts_by_date_range(start_date, end_date)
            
            if transcripts:
                context_parts.append("📋 RECENT MEETINGS:")
                for transcript in transcripts[:3]:
                    meeting_date = transcript.get('metadata', {}).get('meeting_date', 'Unknown')
                    filtered_data = transcript.get('filtered_data', {})
                    ai_analysis = filtered_data.get('ai_analysis', '')
                    
                    context_parts.append(f"• {meeting_date}: {ai_analysis[:200]}..." if ai_analysis else f"• {meeting_date}: Meeting recorded")
            
            # Linear workspace
            try:
                linear_context = self.linear_service.get_workspace_context()
                context_parts.append(f"\n🎯 LINEAR WORKSPACE:")
                context_parts.append(f"• Active Projects: {len(linear_context.projects)}")
                context_parts.append(f"• Open Issues: {len([i for i in linear_context.issues if i.state != 'Done'])}")
                
                for project in linear_context.projects[:3]:
                    context_parts.append(f"• {project.name}: {project.progress or 0:.1f}% complete")
                    
            except Exception as e:
                context_parts.append(f"\n🎯 LINEAR: unavailable ({str(e)[:50]})")
            
            context_parts.append(f"\n🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
        except Exception as e:
            context_parts.append(f"❌ Error gathering context: {str(e)}")
        
        return "\n".join(context_parts) if context_parts else "No context available"
    
    def _get_recent_slack_history(self, channel_id: str, user_id: str, limit: int = 5) -> str:
        """Get recent Slack message history for context."""
        try:
            # This would use Slack API to get recent messages
            # For now, return placeholder
            return f"Recent conversation in channel {channel_id} with user {user_id}"
        except Exception as e:
            return f"Could not retrieve Slack history: {str(e)}"
    
    async def _send_response(self, response_url: str, response: Dict[str, Any]) -> None:
        """Send response back to Slack using response URL."""
        try:
            headers = {"Content-Type": "application/json"}
            requests.post(response_url, json=response, headers=headers, timeout=10)
        except Exception as e:
            print(f"Error sending response to Slack: {e}") 