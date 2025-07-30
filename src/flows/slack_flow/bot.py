"""
Advanced Slack bot for Alpha Machine with AI-powered commands.

Handles all slash commands and interactions with comprehensive context management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

from ...services.slack_service import SlackService
from ...services.supabase_service import SupabaseService
from ...services.ai_service import OpenAIService
from ...services.linear_service import LinearService
from ...services.notion_service import NotionService
from ...core.config import Config
from ...core.models import LinearContext


class SlackBot:
    """Advanced Slack bot for handling AI-powered commands and interactions."""
    
    def __init__(self):
        """Initialize the Slack bot with all required services."""
        self.app = App(token=Config.SLACK_BOT_TOKEN, signing_secret=Config.SLACK_SIGNING_SECRET)
        self.slack_service = SlackService()
        self.supabase_service = SupabaseService()
        self.ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        self.linear_service = LinearService(
            api_key=Config.LINEAR_API_KEY,
            team_name=Config.LINEAR_TEAM_NAME,
            default_assignee=Config.LINEAR_DEFAULT_ASSIGNEE
        )
        self.notion_service = NotionService()
        self._setup_commands()
    
    def _setup_commands(self):
        """Setup all Slack slash commands."""
        
        @self.app.command("/chat")
        def handle_chat_command(ack, command):
            """Handle /chat command for AI conversation with full context."""
            ack()
            
            user_id = command['user_id']
            channel_id = command['channel_id']
            text = command['text']
            
            # Get comprehensive context
            context = self._get_comprehensive_context()
            
            # Generate AI response
            response = self._generate_contextual_response(text, context)
            
            # Send response
            self.slack_service.send_ephemeral_message(
                channel=channel_id,
                user=user_id,
                text=response
            )
        
        @self.app.command("/summarize")
        def handle_summarize_command(ack, command):
            """Handle /summarize command with multiple options."""
            ack()
            
            user_id = command['user_id']
            channel_id = command['channel_id']
            text = command['text']
            
            # Parse command arguments
            args = text.split()
            
            if len(args) >= 2 and args[0] == "last":
                # Handle "last @meeting @timestamp" format
                meeting_info = self._parse_meeting_reference(args[1:])
                summary = self._generate_meeting_summary(meeting_info)
            elif "client" in text.lower():
                # Handle client status summary
                summary = self._generate_client_status_summary(text)
            else:
                summary = "Invalid summarize command format. Use:\n- `/summarize last @meeting @timestamp`\n- `/summarize client [client_name]`"
            
            self.slack_service.send_ephemeral_message(
                channel=channel_id,
                user=user_id,
                text=summary
            )
        
        @self.app.command("/create")
        def handle_create_command(ack, command):
            """Handle /create command for Linear tickets with AI assistance."""
            ack()
            
            user_id = command['user_id']
            channel_id = command['channel_id']
            text = command['text']
            
            # Create Linear tickets based on context and user input
            result = self._create_linear_tickets_with_ai(text)
            
            self.slack_service.send_ephemeral_message(
                channel=channel_id,
                user=user_id,
                text=result
            )
        
        @self.app.command("/teammember")
        def handle_teammember_command(ack, command):
            """Handle /@teammember command for team member information."""
            ack()
            
            user_id = command['user_id']
            channel_id = command['channel_id']
            text = command['text']
            
            # Extract team member info
            team_member_info = self._get_team_member_info(text)
            
            self.slack_service.send_ephemeral_message(
                channel=channel_id,
                user=user_id,
                text=team_member_info
            )
        
        @self.app.command("/weekly-summary")
        def handle_weekly_summary_command(ack, command):
            """Handle automatic weekly summary generation."""
            ack()
            
            user_id = command['user_id']
            channel_id = command['channel_id']
            
            # Generate comprehensive weekly summary
            summary = self._generate_weekly_summary()
            
            self.slack_service.send_ephemeral_message(
                channel=channel_id,
                user=user_id,
                text=summary
            )
    
    def _get_comprehensive_context(self) -> str:
        """Get comprehensive context from multiple sources."""
        context_parts = []
        
        # Get recent transcripts (last 7 days)
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        
        transcripts = self.supabase_service.get_transcripts_by_date_range(start_date, end_date)
        
        if transcripts:
            context_parts.append("RECENT MEETING CONTEXT:")
            for transcript in transcripts[:5]:  # Last 5 transcripts
                meeting_date = transcript.get('metadata', {}).get('meeting_date', 'Unknown date')
                filtered_data = transcript.get('filtered_data', {})
                ai_analysis = filtered_data.get('ai_analysis', '')
                
                context_parts.append(f"\n📅 {meeting_date}:")
                if ai_analysis:
                    context_parts.append(f"   {ai_analysis[:300]}...")
        
        # Get current Linear workspace state
        try:
            linear_context = self.linear_service.get_workspace_context()
            context_parts.append("\n\nCURRENT LINEAR WORKSPACE:")
            context_parts.append(linear_context.format_for_prompt())
        except Exception as e:
            context_parts.append(f"\n\nLinear context unavailable: {str(e)}")
        
        return "\n".join(context_parts)
    
    def _generate_contextual_response(self, user_input: str, context: str) -> str:
        """Generate AI response with comprehensive context."""
        system_prompt = """
        You are Alpha Machine, an AI assistant for a consulting firm. You have access to:
        1. Recent meeting transcripts with AI-filtered commercial/monetary information
        2. Current Linear workspace state (projects, issues, milestones)
        3. Team member information and project statuses
        
        Provide helpful, contextual responses based on the available information.
        Be concise but thorough, and always reference specific data when possible.
        """
        
        user_prompt = f"""
        Context from recent meetings and current workspace:
        {context}
        
        User question: {user_input}
        
        Please provide a helpful response based on the context and your knowledge.
        If referencing specific meetings, projects, or team members, be specific.
        """
        
        try:
            response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            return response[0] if response else "I couldn't generate a response at this time."
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _parse_meeting_reference(self, args: list) -> Dict[str, Any]:
        """Parse meeting reference from command arguments."""
        meeting_info = {
            "args": args,
            "meeting_type": None,
            "timestamp": None
        }
        
        for arg in args:
            if arg.startswith('@'):
                if 'meeting' in arg.lower():
                    meeting_info["meeting_type"] = arg
                elif re.match(r'@\d{1,2}:\d{2}', arg):
                    meeting_info["timestamp"] = arg
        
        return meeting_info
    
    def _generate_meeting_summary(self, meeting_info: Dict[str, Any]) -> str:
        """Generate meeting summary based on meeting reference."""
        try:
            # Get recent transcripts
            end_date = datetime.now().isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            transcripts = self.supabase_service.get_transcripts_by_date_range(start_date, end_date)
            
            if not transcripts:
                return "No recent meetings found."
            
            # Find the most recent meeting or specific timestamp
            target_transcript = transcripts[0]  # Default to most recent
            
            if meeting_info.get("timestamp"):
                # Try to find meeting with specific timestamp
                timestamp = meeting_info["timestamp"].replace('@', '')
                for transcript in transcripts:
                    meeting_time = transcript.get('metadata', {}).get('meeting_time', '')
                    if timestamp in meeting_time:
                        target_transcript = transcript
                        break
            
            # Generate summary using AI
            system_prompt = """
            You are an expert at summarizing meeting transcripts. Create a concise but comprehensive summary that includes:
            1. Key decisions made
            2. Action items and assignments
            3. Important deadlines and timelines
            4. Commercial/monetary information discussed
            5. Next steps
            """
            
            user_prompt = f"""
            Please summarize this meeting transcript:
            
            {target_transcript.get('raw_transcript', '')}
            
            Focus on actionable items and key information.
            """
            
            response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            return response[0] if response else "Unable to generate meeting summary."
            
        except Exception as e:
            return f"Error generating meeting summary: {str(e)}"
    
    def _generate_client_status_summary(self, text: str) -> str:
        """Generate client status summary with deadlines and progress."""
        try:
            # Extract client name from text
            client_match = re.search(r'client\s+(\w+)', text.lower())
            if not client_match:
                return "Please specify a client name: `/summarize client [client_name]`"
            
            client_name = client_match.group(1)
            
            # Get client status from Supabase
            client_status = self.supabase_service.get_client_status(client_name)
            
            # Get Linear projects for this client
            linear_context = self.linear_service.get_workspace_context()
            client_projects = [p for p in linear_context.projects if client_name.lower() in p.name.lower()]
            
            # Get Notion documents for this client
            notion_docs = self.notion_service.get_client_documents(client_name)
            
            # Generate comprehensive summary
            summary_parts = [f"📊 **Client Status Summary: {client_name.title()}**\n"]
            
            if client_status:
                summary_parts.append(f"**Current Status:** {client_status.get('status', 'Unknown')}")
                summary_parts.append(f"**Deadline:** {client_status.get('deadline', 'Not set')}")
                summary_parts.append(f"**Progress:** {client_status.get('progress', '0')}%")
            
            if client_projects:
                summary_parts.append(f"\n**Linear Projects ({len(client_projects)}):**")
                for project in client_projects:
                    summary_parts.append(f"• {project.name} - {project.state or 'Unknown'} ({project.progress or 0:.1f}%)")
                    if project.target_date:
                        summary_parts.append(f"  📅 Target: {project.target_date}")
            
            if notion_docs:
                summary_parts.append(f"\n**Notion Documents ({len(notion_docs)}):**")
                for doc in notion_docs[:5]:  # Show first 5
                    summary_parts.append(f"• {doc.get('title', 'Untitled')}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            return f"Error generating client status summary: {str(e)}"
    
    def _create_linear_tickets_with_ai(self, text: str) -> str:
        """Create Linear tickets using AI analysis of context and user input."""
        try:
            # Get comprehensive context
            context = self._get_comprehensive_context()
            
            # Use AI to generate ticket suggestions
            system_prompt = """
            You are an expert at creating Linear tickets from meeting context and user requirements.
            Analyze the context and user input to suggest appropriate Linear tickets.
            For each ticket, provide:
            1. Title
            2. Description
            3. Priority (0-4, 0=highest)
            4. Estimated time (0.5, 1, 2, 4, 8 hours)
            5. Assignee (if mentioned)
            6. Project (if applicable)
            """
            
            user_prompt = f"""
            Context from recent meetings and current workspace:
            {context}
            
            User request: {text}
            
            Please suggest Linear tickets that should be created based on this context and request.
            """
            
            response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            
            if not response:
                return "Unable to generate ticket suggestions."
            
            # For now, return the AI suggestions
            # In the future, this could actually create the tickets
            return f"🎫 **Suggested Linear Tickets:**\n\n{response[0]}"
            
        except Exception as e:
            return f"Error creating Linear tickets: {str(e)}"
    
    def _get_team_member_info(self, text: str) -> str:
        """Get comprehensive team member information."""
        try:
            # Extract team member name/email from text
            member_match = re.search(r'@(\w+)', text)
            if not member_match:
                return "Please specify a team member: `/teammember @username`"
            
            member_identifier = member_match.group(1)
            
            # Get Linear context for team member's work
            linear_context = self.linear_service.get_workspace_context()
            
            # Find issues assigned to this team member
            member_issues = []
            for issue in linear_context.issues:
                if member_identifier.lower() in (issue.assignee_name or '').lower():
                    member_issues.append(issue)
            
            # Get user info from Slack
            user_info = self.slack_service.get_user_info(member_identifier)
            
            # Generate summary
            summary_parts = [f"👤 **Team Member: {member_identifier}**\n"]
            
            if user_info:
                summary_parts.append(f"**Name:** {user_info.get('real_name', 'Unknown')}")
                summary_parts.append(f"**Status:** {user_info.get('profile', {}).get('status_text', 'No status')}")
            
            if member_issues:
                active_issues = [i for i in member_issues if i.state_type != 'completed']
                completed_issues = [i for i in member_issues if i.state_type == 'completed']
                
                summary_parts.append(f"\n**Active Issues ({len(active_issues)}):**")
                for issue in active_issues[:5]:  # Show first 5
                    summary_parts.append(f"• {issue.title} - {issue.state_name or 'Unknown'}")
                    if issue.project_name:
                        summary_parts.append(f"  📁 Project: {issue.project_name}")
                
                if completed_issues:
                    summary_parts.append(f"\n**Recently Completed ({len(completed_issues)}):**")
                    for issue in completed_issues[-3:]:  # Show last 3
                        summary_parts.append(f"• {issue.title}")
            else:
                summary_parts.append("\n**No active issues found.**")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            return f"Error getting team member info: {str(e)}"
    
    def _generate_weekly_summary(self) -> str:
        """Generate comprehensive weekly summary."""
        try:
            # Get data from the past week
            end_date = datetime.now().isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            # Get transcripts
            transcripts = self.supabase_service.get_transcripts_by_date_range(start_date, end_date)
            
            # Get Linear context
            linear_context = self.linear_service.get_workspace_context()
            
            # Generate summary using AI
            system_prompt = """
            You are an expert at creating weekly summaries for consulting projects.
            Create a comprehensive weekly summary that includes:
            1. Key accomplishments and milestones reached
            2. Important decisions made
            3. Action items and next steps
            4. Project status updates
            5. Upcoming deadlines and priorities
            6. Team performance highlights
            """
            
            # Prepare context data
            context_data = {
                "meetings_this_week": len(transcripts),
                "active_projects": len([p for p in linear_context.projects if p.state != 'completed']),
                "active_issues": len([i for i in linear_context.issues if i.state_type != 'completed']),
                "recent_transcripts": [t.get('metadata', {}).get('meeting_date', 'Unknown') for t in transcripts[:3]]
            }
            
            user_prompt = f"""
            Create a weekly summary based on this data:
            
            **Week Overview:**
            - Meetings held: {context_data['meetings_this_week']}
            - Active projects: {context_data['active_projects']}
            - Active issues: {context_data['active_issues']}
            - Recent meetings: {', '.join(context_data['recent_transcripts'])}
            
            **Linear Workspace State:**
            {linear_context.format_for_prompt()}
            
            Please create a professional weekly summary suitable for stakeholders.
            """
            
            response = self.ai_service._call_openai_structured(system_prompt, user_prompt)
            return response[0] if response else "Unable to generate weekly summary."
            
        except Exception as e:
            return f"Error generating weekly summary: {str(e)}"
    
    def get_handler(self):
        """Get Flask request handler."""
        return SlackRequestHandler(self.app) 