"""
Slack Command Handler for Alpha Machine Bot

Simplified handler that uses prompts.yml and Slack's native history.
"""

import json
import requests
import sys
import traceback
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

from shared.core.config import Config
from shared.core.utils import load_prompts
from shared.services.slack_service import SlackService
from shared.services.ai_service import OpenAIService
from shared.services.linear_service import LinearService
from shared.services.notion_service import NotionService
from shared.services.supabase_service import SupabaseService
from shared.core.models import LinearContext

# Configure logging
logger = logging.getLogger(__name__)

def format_linear_context_comprehensive(linear_context: LinearContext) -> str:
    """
    Format Linear context into a comprehensive, highly organized text structure
    for AI consumption with maximum detail and clarity.
    """
    
    if not linear_context.projects and not linear_context.issues:
        return "📝 LINEAR: No workspace data available"
    
    sections = []
    
    # ============================================================================
    # EXECUTIVE SUMMARY
    # ============================================================================
    total_issues = len(linear_context.issues)
    active_issues = len([i for i in linear_context.issues if i.state_type != 'completed'])
    completed_issues = total_issues - active_issues
    
    sections.append("🎯 LINEAR WORKSPACE CONTEXT")
    sections.append("=" * 50)
    sections.append(f"📊 SUMMARY: {len(linear_context.projects)} projects | {active_issues} active issues | {completed_issues} completed")
    sections.append(f"📈 Completion Rate: {(completed_issues/total_issues*100) if total_issues > 0 else 0:.1f}%")
    sections.append("")
    
    # ============================================================================
    # PROJECTS SECTION - DETAILED VIEW
    # ============================================================================
    sections.append("🚀 ACTIVE PROJECTS:")
    
    if not linear_context.projects:
        sections.append("• No projects found")
    else:
        # Focus on projects with active work
        active_projects = [p for p in linear_context.projects if p.state == 'started']
        backlog_projects = [p for p in linear_context.projects if p.state != 'started']
        
        for project in active_projects:
            sections.append(f"📋 {project.name} ({project.progress or 0:.1f}% complete)")
            if project.description:
                sections.append(f"   📝 {project.description}")
            else:
                sections.append(f"   📝 No description")
            
            # Project milestones
            project_milestones = [m for m in linear_context.milestones if m.project_id == project.id]
            if project_milestones:
                sections.append(f"   🎯 Milestones:")
                for milestone in project_milestones:
                    sections.append(f"     • {milestone.name} (Target: {milestone.target_date or 'TBD'})")
                    if milestone.description:
                        sections.append(f"       📝 {milestone.description}")
            
            # Project issues - focus on active
            project_issues = [iss for iss in linear_context.issues if iss.project_id == project.id]
            active_project_issues = [iss for iss in project_issues if iss.state_type != 'completed']
            
            if active_project_issues:
                sections.append(f"   🔥 Active Issues ({len(active_project_issues)}):")
                for i, issue in enumerate(active_project_issues, 1):  # Show ALL issues with numbering
                    priority_emoji = "🔴" if issue.priority == 1 else "🟡" if issue.priority == 2 else "🟢" if issue.priority == 3 else "⚪"
                    assignee = issue.assignee_name or "Unassigned"
                    
                    # Clear issue separator with title
                    sections.append(f"   ┌─ Issue #{i}: {priority_emoji} {issue.title}")
                    sections.append(f"   │  👤 {assignee} | ⏱️ {issue.estimate or 'No'}h | Status: {issue.state_name}")
                    if issue.description:
                        # Properly indent description within the box
                        desc_lines = issue.description.split('\n')
                        for desc_line in desc_lines:
                            if desc_line.strip():
                                sections.append(f"   │  📝 {desc_line.strip()}")
                    sections.append(f"   └─────────────────────────────────────────────")
                    sections.append("")  # Extra spacing between issues
            else:
                sections.append(f"   📋 No active issues")
            
            sections.append("")
    
    # ============================================================================
    # TEAM WORKLOAD SECTION
    # ============================================================================
    sections.append("👥 TEAM WORKLOAD:")
    
    # Group active issues by assignee
    assignee_workload = {}
    active_issues_list = [iss for iss in linear_context.issues if iss.state_type != 'completed']
    
    for issue in active_issues_list:
        assignee = issue.assignee_name or "Unassigned"
        if assignee not in assignee_workload:
            assignee_workload[assignee] = []
        assignee_workload[assignee].append(issue)
    
    if not assignee_workload:
        sections.append("• No active issues assigned")
    else:
        for assignee, issues in sorted(assignee_workload.items(), key=lambda x: len(x[1]), reverse=True):
            total_estimate = sum(iss.estimate or 0 for iss in issues)
            high_priority = len([iss for iss in issues if iss.priority == 1])
            
            sections.append(f"👤 {assignee}: {len(issues)} issues | {total_estimate}h total | {high_priority} high priority")
            
            # Show ALL issues for this person with clear separation
            for i, issue in enumerate(issues, 1):
                priority_emoji = "🔴" if issue.priority == 1 else "🟡" if issue.priority == 2 else "🟢"
                sections.append(f"   ├─ #{i}: {priority_emoji} {issue.title}")
                if issue.description:
                    # Properly indent description for team workload
                    desc_lines = issue.description.split('\n')
                    for desc_line in desc_lines:
                        if desc_line.strip():
                            sections.append(f"   │    📝 {desc_line.strip()}")
                sections.append(f"   │")  # Spacing between issues
    
    sections.append("")
    
    # ============================================================================
    # UPCOMING MILESTONES
    # ============================================================================
    if linear_context.milestones:
        sections.append("🎯 UPCOMING MILESTONES:")
        
        # Sort by target date
        sorted_milestones = sorted(
            [m for m in linear_context.milestones if m.target_date], 
            key=lambda m: m.target_date
        )
        
        for milestone in sorted_milestones:
            milestone_issues = [iss for iss in linear_context.issues if iss.milestone_id == milestone.id and iss.state_type != 'completed']
            sections.append(f"📍 {milestone.name} (Target: {milestone.target_date})")
            sections.append(f"   🚀 Project: {milestone.project_name}")
            if milestone.description:
                sections.append(f"   📝 {milestone.description}")
            sections.append(f"   📋 Active Issues: {len(milestone_issues)}")
        
        sections.append("")
    
    sections.append("=" * 50)
    
    return "\n".join(sections)

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
        
        logger.info(f"BACKGROUND TASK: Starting to process command: {command}")
        print(f"=== BACKGROUND TASK: Starting to process command: {command} ===", flush=True)
        
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
            
            # Convert string responses to proper Slack format
            if isinstance(response, str):
                response = {
                    "response_type": "in_channel",
                    "text": response
                }
            
            logger.info(f"BACKGROUND TASK: About to send response to {response_url}")
            print(f"=== BACKGROUND TASK: About to send response to Slack ===", flush=True)
            await self._send_response(response_url, response)
            logger.info(f"BACKGROUND TASK: Response sent successfully")
            print(f"=== BACKGROUND TASK: Response sent successfully ===", flush=True)
            
        except Exception as e:
            logger.error(f"BACKGROUND TASK ERROR: {type(e).__name__}: {str(e)}")
            print(f"=== BACKGROUND TASK ERROR: {type(e).__name__}: {str(e)} ===", flush=True)
            print(f"=== BACKGROUND TASK TRACEBACK: {traceback.format_exc()} ===", flush=True)
            error_response = {
                "response_type": "ephemeral",
                "text": f"❌ Error processing {command}: {str(e)}"
            }
            await self._send_response(response_url, error_response)
    
    async def handle_command_sync(self, payload: Dict[str, Any]) -> str:
        """SYNCHRONOUS version - returns AI response text directly (for testing)."""
        command = payload.get("command", "")
        
        print(f"=== SYNC HANDLER: Processing {command} ===", flush=True)
        
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
                return f"Unknown command: {command}"
            
            # Extract just the text from the response
            if isinstance(response, str):
                response_text = response
            else:
                response_text = response.get("text", "No response text")
            print(f"=== SYNC HANDLER: Generated response: {response_text[:100]}... ===", flush=True)
            return response_text
            
        except Exception as e:
            print(f"=== SYNC HANDLER ERROR: {str(e)} ===", flush=True)
            print(f"=== SYNC HANDLER TRACEBACK: {traceback.format_exc()} ===", flush=True)
            return f"❌ Error processing {command}: {str(e)}"
    
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
            # Use the async text generation method for chat responses
            print(f"=== CHAT: About to call AI service with model: {self.ai_service.model} ===", flush=True)
            print(f"=== CHAT: AI service client type: {type(self.ai_service.client)} ===", flush=True)
            print(f"=== CHAT: System prompt length: {len(system_prompt)} ===", flush=True)
            print(f"=== CHAT: User prompt length: {len(user_prompt)} ===", flush=True)
            
            # Call AI service to generate response
            response_text = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            
            print(f"=== CHAT: AI service returned response of length: {len(response_text) if response_text else 0} ===", flush=True)
            print(f"=== CHAT: AI RESPONSE CONTENT: {response_text} ===", flush=True)

            if response_text:
                return f"🤖 **AI Response:**\n{response_text}"
            else:
                return "🤖 **AI Response:**\nI couldn't generate a response at this time."
        
        except Exception as e:
            print(f"=== CHAT AI ERROR: {type(e).__name__}: {str(e)} ===", flush=True)
            print(f"=== CHAT AI TRACEBACK: {traceback.format_exc()} ===", flush=True)
            
            logger.error(f"CHAT AI ERROR: {type(e).__name__}: {str(e)}")
            logger.error(f"CHAT AI TRACEBACK: {traceback.format_exc()}")
            response_text = f"AI Exception: {type(e).__name__}: {str(e)}"
        
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
            # Use async text generation for create tickets
            ai_response = await self.ai_service._call_openai_structured_async(system_prompt, user_prompt)
            
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
                "text": f"❌ **Error:** The AI returned an invalid format. Analysis:\n\n{ai_response[0] if 'ai_response' in locals() else 'No response'}"
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
            # Use async text generation for update tickets
            ai_response = await self.ai_service._call_openai_structured_async(system_prompt, user_prompt)
            
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
                "text": f"❌ **Error:** The AI returned an invalid format. Analysis:\n\n{ai_response[0] if 'ai_response' in locals() else 'No response'}"
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
            # Use async text generation for team member info
            ai_response = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            ai_response = ai_response if ai_response else "No information found for this team member."
            
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
            # Use async text generation for weekly summary
            ai_response = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            ai_response = ai_response if ai_response else "Unable to generate weekly summary."
            
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
            
            # Use async text generation for meeting summary
            summary = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            summary = summary if summary else "Unable to generate meeting summary."
            
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
            
            # Use async text generation for client summary
            summary = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            summary = summary if summary else f"No information found for client: {client_name}"
            
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
        """Get comprehensive context from all sources with full Linear workspace detail."""
        context_parts = []
        
        # Recent transcripts (handle database errors gracefully)
        try:
            end_date = datetime.now().isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            transcripts = self.supabase_service.get_filtered_transcripts_by_date_range(start_date, end_date)
            
            if transcripts:
                context_parts.append("📋 RECENT MEETINGS (Last 7 Days):")
                context_parts.append("-" * 35)
                for transcript in transcripts[:3]:
                    meeting_date = transcript.get('metadata', {}).get('meeting_date', 'Unknown')
                    filtered_data = transcript.get('filtered_data', {})
                    ai_analysis = filtered_data.get('ai_analysis', '')
                    
                    context_parts.append(f"• {meeting_date}: {ai_analysis[:200]}..." if ai_analysis else f"• {meeting_date}: Meeting recorded")
                context_parts.append("")
        except Exception as e:
            # Don't let database errors stop the entire context retrieval
            print(f"=== CONTEXT: Transcript retrieval failed: {str(e)} ===", flush=True)
            context_parts.append("📋 MEETINGS: Database unavailable")
            context_parts.append("")
        
        # Comprehensive Linear workspace context
        try:
            linear_context = self.linear_service.get_workspace_context()
            linear_formatted = format_linear_context_comprehensive(linear_context)
            context_parts.append(linear_formatted)
                
        except Exception as e:
            context_parts.append(f"🎯 LINEAR: unavailable ({str(e)[:50]})")
            context_parts.append("")
        
        context_parts.append(f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(context_parts) if context_parts else "📝 Basic AI assistant ready to help"
    
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
            # Use a shorter timeout for the response to Slack
            response_result = requests.post(response_url, json=response, headers=headers, timeout=5)
            if response_result.status_code != 200:
                logger.warning(f"Failed to send response to Slack: {response_result.status_code} - {response_result.text}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout sending response to Slack: {response_url}")
            # Try once more with a fallback message
            try:
                fallback_response = {
                    "response_type": "ephemeral",
                    "text": "⚠️ Response took longer than expected. The operation may still be processing."
                }
                requests.post(response_url, json=fallback_response, headers=headers, timeout=3)
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback response: {fallback_error}")
        except Exception as e:
            logger.error(f"Error sending response to Slack: {e}") 