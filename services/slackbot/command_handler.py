"""
Slack Command Handler for Alpha Machine Bot

Simplified handler that uses prompts.yml and Slack's native history.
"""

import asyncio
import json
import requests
import sys
import traceback
from typing import Dict, Any, List, Optional
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

# Global storage for user transcript selections (in production, use Redis or database)
USER_TRANSCRIPT_SELECTIONS = {}
SELECTION_TIMEOUT_MINUTES = 10

# Global storage for pending ticket creations
USER_PENDING_TICKETS = {}
PENDING_TICKET_TIMEOUT_MINUTES = 10

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
    
    def _store_user_selection(self, user_id: str, transcript_ids: List[str]) -> None:
        """Store user's transcript selection with timestamp."""
        USER_TRANSCRIPT_SELECTIONS[user_id] = {
            'transcript_ids': transcript_ids,
            'timestamp': datetime.now()
        }
    
    def _get_user_selection(self, user_id: str) -> Optional[List[str]]:
        """Get user's stored transcript selection if still valid."""
        if user_id not in USER_TRANSCRIPT_SELECTIONS:
            return None
        
        selection_data = USER_TRANSCRIPT_SELECTIONS[user_id]
        timestamp = selection_data['timestamp']
        
        # Check if selection has expired
        if datetime.now() - timestamp > timedelta(minutes=SELECTION_TIMEOUT_MINUTES):
            del USER_TRANSCRIPT_SELECTIONS[user_id]
            return None
        
        return selection_data['transcript_ids']
    
    def _clear_user_selection(self, user_id: str) -> None:
        """Clear user's transcript selection."""
        if user_id in USER_TRANSCRIPT_SELECTIONS:
            del USER_TRANSCRIPT_SELECTIONS[user_id]
    
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
        
        # Check if user wants to select transcripts interactively
        if text.lower() in ["select", "choose", "pick", "transcripts"]:
            return await self._show_transcript_selector_for_chat(channel_id, user_id)
        elif text.lower().startswith("with "):
            # User typed "/chat with [question]" 
            question = text[5:].strip()  # Remove "with " prefix
            if question:
                return await self._handle_chat_with_selector_inline(payload, question)
            else:
                return await self._show_transcript_selector_for_chat(channel_id, user_id)
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please provide a question or message to chat about.\n\n💡 **Tips**:\n• `/chat select` - Choose specific transcripts\n• `/chat with [question]` - Choose transcripts for your question\n• `/chat [question]` - Use all recent context"
            }
        
        # Check if user has selected specific transcripts
        selected_transcript_ids = self._get_user_selection(user_id)
        
        if selected_transcript_ids:
            # Use selected transcripts and clear the selection
            print(f"=== CHAT: Using {len(selected_transcript_ids)} selected transcripts for user {user_id} ===", flush=True)
            self._clear_user_selection(user_id)  # Clear after use
            return await self._handle_chat_with_selected_transcripts(selected_transcript_ids, text)
        
        # Get context and recent Slack history (default behavior)
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
            
            print(f"=== CHAT: AI service returned response of length: {len(response_text)} ===", flush=True)
            print(f"=== CHAT: AI RESPONSE CONTENT: {response_text} ===", flush=True)
            
            return {
                "response_type": "ephemeral",
                "text": f"🤖 **AI Response:**\n{response_text}"
            }
            
        except Exception as e:
            print(f"=== CHAT ERROR: {str(e)} ===", flush=True)
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error generating response: {str(e)}"
            }

    async def _handle_chat_with_selector(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /chat-with command - shows transcript selector with user's question."""
        text = payload.get("text", "").strip()
        channel_id = payload.get("channel_id", "")
        user_id = payload.get("user_id", "")
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please provide your question.\n\n💡 **Usage**: `/chat-with What budget decisions were made?`"
            }
        
        try:
            # Get recent transcripts for selection
            transcripts = self.supabase_service.get_recent_transcripts(limit=10)
            
            if not transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "📭 No transcripts available for selection."
                }
            
            # Build options for the dropdown
            options = []
            for transcript in transcripts:
                filename = transcript.get('filename', 'Unknown Meeting')
                created_date = transcript.get('created_at', 'Unknown date')
                transcript_id = transcript.get('id', '')
                
                # Format date for display
                try:
                    if created_date and created_date != 'Unknown date':
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%m/%d %H:%M')
                    else:
                        formatted_date = 'Unknown date'
                except:
                    formatted_date = str(created_date)[:10] if created_date else 'Unknown date'
                
                # Create option for dropdown
                option_text = f"{filename} ({formatted_date})"
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": option_text[:75]  # Slack limit
                    },
                    "value": transcript_id
                })
            
            # Create the interactive message with dropdown and user's question
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🎯 **Your Question**: {text}\n\n📋 *Select which transcripts to analyze:*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎛️ *Choose transcripts for context:*"
                    },
                    "accessory": {
                        "type": "multi_static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose transcripts..."
                        },
                        "options": options,
                        "action_id": "chat_with_transcript_selection"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🚀 Answer with Selected"
                            },
                            "style": "primary",
                            "action_id": "answer_with_selected",
                            "value": text  # Store the user's question
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📋 Use All Recent"
                            },
                            "action_id": "answer_with_all",
                            "value": text  # Store the user's question
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 Select transcripts above, then click a button to get your AI-powered answer."
                        }
                    ]
                }
            ]
            
            return {
                "response_type": "ephemeral",
                "blocks": blocks
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error showing transcript selector: {str(e)}"
            }

    async def _handle_chat_with_selector_inline(self, payload: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Handle inline /chat with [question] - shows selector with the question embedded."""
        try:
            # Get recent transcripts for selection
            transcripts = self.supabase_service.get_recent_transcripts(limit=10)
            
            if not transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "📭 No transcripts available for selection."
                }
            
            # Build options for the dropdown
            options = []
            for transcript in transcripts:
                filename = transcript.get('filename', 'Unknown Meeting')
                created_date = transcript.get('created_at', 'Unknown date')
                transcript_id = transcript.get('id', '')
                
                # Format date for display
                try:
                    if created_date and created_date != 'Unknown date':
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%m/%d %H:%M')
                    else:
                        formatted_date = 'Unknown date'
                except:
                    formatted_date = str(created_date)[:10] if created_date else 'Unknown date'
                
                # Create option for dropdown
                option_text = f"{filename} ({formatted_date})"
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": option_text[:75]  # Slack limit
                    },
                    "value": transcript_id
                })
            
            # Create the interactive message with dropdown and user's question
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🎯 **Your Question**: {question}\n\n📋 *Select which transcripts to analyze:*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎛️ *Choose transcripts for context:*"
                    },
                    "accessory": {
                        "type": "multi_static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose transcripts..."
                        },
                        "options": options,
                        "action_id": "chat_inline_transcript_selection"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🚀 Answer with Selected"
                            },
                            "style": "primary",
                            "action_id": "answer_inline_selected",
                            "value": question  # Store the user's question
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📋 Use All Recent"
                            },
                            "action_id": "answer_inline_all",
                            "value": question  # Store the user's question
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 Select transcripts above, then click a button to get your AI-powered answer."
                        }
                    ]
                }
            ]
            
            return {
                "response_type": "ephemeral",
                "blocks": blocks
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error showing transcript selector: {str(e)}"
            }

    async def _show_transcript_selector_for_chat(self, channel_id: str, user_id: str) -> Dict[str, Any]:
        """Show transcript selector for /chat select (without a predefined question)."""
        try:
            # Get recent transcripts for selection
            transcripts = self.supabase_service.get_recent_transcripts(limit=10)
            
            if not transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "📭 No transcripts available for selection."
                }
            
            # Build options for the dropdown
            options = []
            for transcript in transcripts:
                filename = transcript.get('filename', 'Unknown Meeting')
                created_date = transcript.get('created_at', 'Unknown date')
                transcript_id = transcript.get('id', '')
                
                # Format date for display
                try:
                    if created_date and created_date != 'Unknown date':
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%m/%d %H:%M')
                    else:
                        formatted_date = 'Unknown date'
                except:
                    formatted_date = str(created_date)[:10] if created_date else 'Unknown date'
                
                # Create option for dropdown
                option_text = f"{filename} ({formatted_date})"
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": option_text[:75]  # Slack limit
                    },
                    "value": transcript_id
                })
            
            # Create the interactive message for selection only
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "📋 **Select Transcripts** for your next `/chat` command:\n\n🎛️ *Choose which transcripts to use as context:*"
                    },
                    "accessory": {
                        "type": "multi_static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose transcripts..."
                        },
                        "options": options,
                        "action_id": "chat_select_transcript_selection"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Set Selection"
                            },
                            "style": "primary",
                            "action_id": "set_transcript_selection"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 After setting your selection, use `/chat [your question]` and it will use only the selected transcripts."
                        }
                    ]
                }
            ]
            
            return {
                "response_type": "ephemeral",
                "blocks": blocks
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error showing transcript selector: {str(e)}"
            }

    async def _show_transcript_selector(self, channel_id: str, user_id: str) -> Dict[str, Any]:
        """Show interactive transcript selection dropdown."""
        try:
            # Get recent transcripts for selection
            transcripts = self.supabase_service.get_recent_transcripts(limit=10)
            
            if not transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "📭 No transcripts available for selection."
                }
            
            # Build options for the dropdown
            options = []
            for transcript in transcripts:
                filename = transcript.get('filename', 'Unknown Meeting')
                created_date = transcript.get('created_at', 'Unknown date')
                transcript_id = transcript.get('id', '')
                
                # Format date for display
                try:
                    if created_date and created_date != 'Unknown date':
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%m/%d %H:%M')
                    else:
                        formatted_date = 'Unknown date'
                except:
                    formatted_date = str(created_date)[:10] if created_date else 'Unknown date'
                
                # Create option for dropdown
                option_text = f"{filename} ({formatted_date})"
                options.append({
                    "text": {
                        "type": "plain_text",
                        "text": option_text[:75]  # Slack limit
                    },
                    "value": transcript_id
                })
            
            # Create the interactive message with dropdown
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "📋 *Select transcripts to include in your chat context:*\nChoose one or multiple transcripts, then ask your question."
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎯 *Available Transcripts:*"
                    },
                    "accessory": {
                        "type": "multi_static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose transcripts..."
                        },
                        "options": options,
                        "action_id": "transcript_selection"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Use Selected"
                            },
                            "style": "primary",
                            "action_id": "use_selected_transcripts",
                            "value": "confirm"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🔄 Use All Recent"
                            },
                            "action_id": "use_all_transcripts",
                            "value": "all"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 After selecting, use `/chat [your question]` to ask with chosen context."
                        }
                    ]
                }
            ]
            
            return {
                "response_type": "ephemeral",
                "blocks": blocks
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error showing transcript selector: {str(e)}"
            }

    async def _handle_chat_with_selected_transcripts(self, transcript_ids: List[str], user_question: str) -> Dict[str, Any]:
        """Handle chat command with user-selected transcripts."""
        try:
            print(f"=== SELECTED TRANSCRIPTS: Processing {len(transcript_ids)} transcript(s) ===", flush=True)
            start_time = datetime.now()
            
            # Get selected transcripts
            selected_transcripts = []
            for transcript_id in transcript_ids:
                transcript = self.supabase_service.get_transcript_by_id(transcript_id)
                if transcript:
                    selected_transcripts.append(transcript)
            
            fetch_time = datetime.now()
            print(f"=== SELECTED TRANSCRIPTS: Fetched in {(fetch_time - start_time).total_seconds():.2f}s ===", flush=True)
            
            if not selected_transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ Could not retrieve selected transcripts."
                }
            
            # Build custom context with selected transcripts
            context_parts = []
            
            # Selected transcripts context (FULL CONTENT)
            context_parts.append("📋 SELECTED MEETING TRANSCRIPTS (COMPLETE CONTENT):")
            context_parts.append("=" * 60)
            context_parts.append(f"NOTE: You have access to ONLY these {len(selected_transcripts)} selected transcript(s). Do NOT reference any other meetings or transcripts.")
            context_parts.append("=" * 60)
            
            for i, transcript in enumerate(selected_transcripts, 1):
                filename = transcript.get('filename', 'Unknown Meeting')
                created_date = transcript.get('created_at', 'Unknown date')
                transcript_content = transcript.get('filtered_transcript', '')
                
                # Format date
                try:
                    if created_date and created_date != 'Unknown date':
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    else:
                        formatted_date = 'Unknown date'
                except:
                    formatted_date = str(created_date)[:10] if created_date else 'Unknown date'
                
                context_parts.append(f"📄 TRANSCRIPT #{i}: {filename}")
                context_parts.append(f"📅 Date: {formatted_date}")
                context_parts.append("-" * 40)
                
                # Include COMPLETE transcript content (no truncation)
                if transcript_content:
                    context_parts.append(transcript_content.strip())
                else:
                    context_parts.append("No content available")
                
                context_parts.append("-" * 40)
                context_parts.append("")
            
            # Add Linear context
            try:
                linear_context = self.linear_service.get_workspace_context()
                linear_formatted = format_linear_context_comprehensive(linear_context)
                context_parts.append(linear_formatted)
            except Exception as e:
                context_parts.append(f"🎯 LINEAR: unavailable ({str(e)[:50]})")
            
            context_parts.append(f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            custom_context = "\n".join(context_parts)
            context_time = datetime.now()
            print(f"=== SELECTED TRANSCRIPTS: Context built in {(context_time - fetch_time).total_seconds():.2f}s ===", flush=True)
            
            # Generate AI response with custom context
            prompt_config = self.prompts.get('slack_bot_chat')
            if not prompt_config:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ Chat prompt configuration not found."
                }
            
            system_prompt = prompt_config['system_prompt']
            user_prompt = prompt_config['user_prompt'].format(
                context=custom_context,
                user_message=user_question
            )
            
            print(f"=== SELECTED TRANSCRIPTS: Calling AI with context size: {len(custom_context)} chars ===", flush=True)
            response_text = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            ai_time = datetime.now()
            print(f"=== SELECTED TRANSCRIPTS: AI response in {(ai_time - context_time).total_seconds():.2f}s ===", flush=True)
            
            # Build transcript list for response header
            transcript_list = ", ".join([t.get('filename', 'Unknown') for t in selected_transcripts])
            
            total_time = datetime.now()
            print(f"=== SELECTED TRANSCRIPTS: Total processing time: {(total_time - start_time).total_seconds():.2f}s ===", flush=True)
            
            return {
                "response_type": "ephemeral",
                "text": f"🎯 **AI Response** (using ONLY {len(selected_transcripts)} selected transcript(s): {transcript_list}):\n\n{response_text}"
            }
            
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error processing chat with selected transcripts: {str(e)}"
            }
    
    async def _handle_summarize_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /summarize command using prompts.yml."""
        text = payload.get("text", "").strip()
        
        # If no text provided, summarize the most recent meeting
        if not text:
            return await self._handle_meeting_summary([])
        
        args = text.split()
        
        # Handle different summarize options
        if args[0].lower() in ["last", "recent", "latest"]:
            return await self._handle_meeting_summary(args[1:])
        elif "client" in text.lower():
            return await self._handle_client_summary(text)
        else:
            # Default to meeting summary for any other text
            return await self._handle_meeting_summary([])
    
    async def _handle_create_ticket_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /create-ticket command.
        
        Shows AI analysis and asks for user confirmation before creating tickets.
        """
        text = payload.get("text", "").strip()
        user_id = payload.get("user_id")
        
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please describe what you want to create in Linear."
            }
        
        # Add timing to identify bottlenecks
        start_time = datetime.now()
        print(f"=== CREATE TICKET TIMING: Starting at {start_time} ===")
        
        context_start = datetime.now()
        context = await self._get_comprehensive_context()
        context_time = datetime.now()
        print(f"=== CREATE TICKET TIMING: Context fetched in {(context_time - context_start).total_seconds():.2f}s ===")
        
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
            # Use async text generation for create tickets analysis
            ai_start = datetime.now()
            print(f"=== CREATE TICKET TIMING: Starting AI call at {ai_start} ===")
            
            # Truncate context to reduce OpenAI call time
            max_context_length = 8000  # Limit context to avoid slow API calls
            truncated_context = context[:max_context_length] + "..." if len(context) > max_context_length else context
            
            truncated_user_prompt = prompt_config['user_prompt'].format(
                context=truncated_context,
                ticket_description=text
            )
            
            ai_response = await self.ai_service._call_openai_structured_async(system_prompt, truncated_user_prompt)
            ai_end = datetime.now()
            analysis = ai_response[0]
            print(f"=== CREATE TICKET TIMING: AI completed in {(ai_end - ai_start).total_seconds():.2f}s ===")
            print(f"=== CREATE TICKET TIMING: Analysis length: {len(analysis)} chars ===")
            print(f"=== CREATE TICKET TIMING: Context length: {len(truncated_context)} chars ===")
            
            # Store the pending ticket creation data
            ticket_data = {
                "context": context,
                "original_request": text,
                "analysis": analysis,
                "timestamp": datetime.now(),
                "user_id": user_id
            }
            
            # Store for this user (will expire after timeout)
            USER_PENDING_TICKETS[user_id] = ticket_data
            
            # Always show analysis with YES/NO buttons (regardless of test mode)
            test_mode_indicator = " [TEST MODE]" if Config.LINEAR_TEST_MODE else ""
            
            # Limit analysis text for Slack blocks (max 3000 chars to be safe)
            max_analysis_length = 2800
            truncated_analysis = analysis[:max_analysis_length] + "..." if len(analysis) > max_analysis_length else analysis
            
            # Clean the analysis text for Slack markdown (escape problematic characters)
            cleaned_analysis = truncated_analysis.replace('*', '•').replace('`', "'")
            
            total_time = datetime.now()
            print(f"=== CREATE TICKET TIMING: Total time {(total_time - start_time).total_seconds():.2f}s ===")
            
            # Prepare compact payload for interactive button value to avoid cross-instance state loss
            # Limit analysis to keep under Slack's 2000 char value limit
            compact_payload = {
                "user_id": user_id,
                "original_request": text,
                "analysis": (analysis[:1400] + "..." if len(analysis) > 1400 else analysis)
            }
            compact_payload_str = json.dumps(compact_payload)

            return {
                "response_type": "ephemeral",
                "text": f"📋 Linear Ticket Analysis{test_mode_indicator}:\n\n{cleaned_analysis}\n\n⚡ Would you like me to create these tickets in Linear?",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📋 *Linear Ticket Analysis{test_mode_indicator}:*\n\n{cleaned_analysis}\n\n⚡ *Would you like me to create these tickets in Linear?*"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "✅ Yes, Create Tickets"
                                },
                                "style": "primary",
                                "action_id": "create_tickets_yes",
                                "value": compact_payload_str
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "❌ No, Cancel"
                                },
                                "style": "danger",
                                "action_id": "create_tickets_no",
                                "value": compact_payload_str
                            }
                        ]
                    }
                ]
            }
                
        except Exception as e:
            return {
                "response_type": "ephemeral", 
                "text": f"❌ Error processing ticket creation: {str(e)}"
            }

    def _get_pending_tickets(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get pending ticket creation data for a user, checking timeout."""
        if user_id not in USER_PENDING_TICKETS:
            return None
        
        ticket_data = USER_PENDING_TICKETS[user_id]
        
        # Check if the selection has expired
        if datetime.now() - ticket_data["timestamp"] > timedelta(minutes=PENDING_TICKET_TIMEOUT_MINUTES):
            del USER_PENDING_TICKETS[user_id]
            return None
        
        return ticket_data

    def _clear_pending_tickets(self, user_id: str) -> None:
        """Clear pending ticket creation data for a user."""
        if user_id in USER_PENDING_TICKETS:
            del USER_PENDING_TICKETS[user_id]

    async def handle_create_tickets_confirmation(self, user_id: str, confirmed: bool) -> Dict[str, Any]:
        """Handle YES/NO confirmation for ticket creation."""
        ticket_data = self._get_pending_tickets(user_id)
        
        if not ticket_data:
            return {
                "response_type": "ephemeral",
                "text": "❌ **No pending ticket creation found.** Please use `/create` again to generate new tickets."
            }
        
        # Clear the pending data
        self._clear_pending_tickets(user_id)
        
        if not confirmed:
            return {
                "response_type": "ephemeral",
                "text": "✅ **Ticket creation cancelled.** No tickets were created in Linear."
            }
        
        # User confirmed - create the tickets
        try:
            # Use the structured prompt to convert analysis to JSON
            structured_prompt_config = self.prompts.get('slack_bot_create_tickets_structured')
            if not structured_prompt_config:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ Structured tickets prompt configuration not found."
                }
            
            print(f"=== TICKET CREATION: Starting structured conversion ===")
            conversion_start = datetime.now()
            
            # Use minimal context for faster conversion
            system_prompt = structured_prompt_config['system_prompt']
            user_prompt = structured_prompt_config['user_prompt'].format(
                context="", # Empty context for faster processing
                ticket_description=ticket_data["original_request"],
                analysis=ticket_data["analysis"][:4000]  # Limit analysis length
            )
            
            # Get structured JSON response
            structured_response = await self.ai_service._call_openai_structured_async(system_prompt, user_prompt)
            conversion_end = datetime.now()
            print(f"=== TICKET CREATION: Conversion completed in {(conversion_end - conversion_start).total_seconds():.2f}s ===")
            
            # Parse JSON tickets
            tickets_json = json.loads(structured_response[0])
            
            # Create tickets in Linear
            created_tickets = []
            for ticket_data_item in tickets_json:
                # Normalize keys from structured output to LinearService schema
                mapped_issue = {
                    # LinearService expects 'issue_title' and 'issue_description'
                    'issue_title': ticket_data_item.get('issue_title') or ticket_data_item.get('title'),
                    'issue_description': ticket_data_item.get('issue_description') or ticket_data_item.get('description'),
                    # Optional fields
                    'priority': ticket_data_item.get('priority'),
                    'time_estimate': ticket_data_item.get('time_estimate') or ticket_data_item.get('estimate'),
                    'assign_team_member': ticket_data_item.get('assign_team_member') or ticket_data_item.get('assignee'),
                    'team': ticket_data_item.get('team'),
                    # Project/milestone may be provided as names or ids depending on prompt used
                    'project': ticket_data_item.get('project'),
                    'milestone': ticket_data_item.get('milestone'),
                    'project_id': ticket_data_item.get('project_id'),
                    'milestone_id': ticket_data_item.get('milestone_id'),
                    'deadline': ticket_data_item.get('deadline'),
                }
                
                # In test mode, ensure title is prefixed
                if Config.LINEAR_TEST_MODE and mapped_issue.get('issue_title'):
                    if not mapped_issue['issue_title'].startswith('[TEST]'):
                        mapped_issue['issue_title'] = f"[TEST] {mapped_issue['issue_title']}"
                
                # Create the issue in Linear
                created_issue = self.linear_service.create_issue(mapped_issue)
                if created_issue:
                    created_tickets.append(created_issue)
            
            if created_tickets:
                ticket_list = "\n".join([f"• **{t['title']}** (ID: {t['id']})" for t in created_tickets])
                test_mode_note = " (TEST MODE)" if Config.LINEAR_TEST_MODE else ""
                return {
                    "response_type": "in_channel",
                    "text": f"✅ **{len(created_tickets)} Ticket(s) Created in Linear{test_mode_note}:**\n\n{ticket_list}"
                }
            else:
                return {
                    "response_type": "ephemeral",
                    "text": f"❌ **Failed to create Linear tickets.** The analysis was:\n\n{ticket_data['analysis']}"
                }
                
        except json.JSONDecodeError as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ **Error:** Failed to parse ticket data. {str(e)}"
            }
        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error creating tickets: {str(e)}"
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
            # Use the correct method to get recent transcripts
            transcripts = self.supabase_service.get_recent_transcripts(limit=1)
            
            if not transcripts:
                return {
                    "response_type": "ephemeral",
                    "text": "📭 No recent meetings found."
                }
            
            recent_meeting = transcripts[0]
            # Use the correct database schema columns
            filename = recent_meeting.get('filename', 'Unknown Meeting')
            created_date = recent_meeting.get('created_at', 'Unknown date')
            transcript_content = recent_meeting.get('filtered_transcript', '')
            
            if not transcript_content:
                return {
                    "response_type": "ephemeral", 
                    "text": "📭 No transcript content found for recent meeting."
                }
            
            # Format the date for display
            try:
                if created_date and created_date != 'Unknown date':
                    date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                else:
                    formatted_date = 'Unknown date'
            except:
                formatted_date = str(created_date)[:10] if created_date else 'Unknown date'
            
            prompt_config = self.prompts.get('slack_bot_summarize_meeting')
            if not prompt_config:
                return {
                    "response_type": "ephemeral",
                    "text": "❌ Meeting summary prompt configuration not found."
                }
            
            system_prompt = prompt_config['system_prompt']
            user_prompt = prompt_config['user_prompt'].format(
                context=f"Meeting: {filename} | Date: {formatted_date}",
                meeting_transcript=transcript_content[:3000]
            )
            
            # Use async text generation for meeting summary
            summary = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            summary = summary if summary else "Unable to generate meeting summary."
            
            return {
                "response_type": "ephemeral",
                "text": f"📅 **Meeting Summary - {filename}**\n*{formatted_date}*\n\n{summary}"
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
            # Get most recent transcripts (using created_at since meeting_date doesn't exist)
            transcripts = self.supabase_service.get_recent_transcripts(limit=3)
            
            if transcripts:
                context_parts.append("📋 RECENT MEETINGS (Last 7 Days):")
                context_parts.append("-" * 35)
                for transcript in transcripts:
                    # Use actual database schema columns
                    filename = transcript.get('filename', 'Unknown Meeting')
                    created_date = transcript.get('created_at', 'Unknown Date')
                    transcript_content = transcript.get('filtered_transcript', '')
                    
                    # Extract first few lines as summary since no ai_analysis exists
                    content_preview = transcript_content[:300].replace('\n', ' ').strip() if transcript_content else 'No content available'
                    
                    # Format the date for display
                    try:
                        if created_date and created_date != 'Unknown Date':
                            date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                            formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                        else:
                            formatted_date = 'Unknown Date'
                    except:
                        formatted_date = str(created_date)[:10] if created_date else 'Unknown Date'
                    
                    context_parts.append(f"• {filename} ({formatted_date})")
                    context_parts.append(f"  📝 {content_preview}...")
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
            # Prefer replacing the initial ack message to keep ordering tidy in the channel UI
            if "replace_original" not in response:
                response["replace_original"] = True
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