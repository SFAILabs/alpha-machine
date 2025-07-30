"""
Context manager service for efficient context loading across Slack bot functions.
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from ...core.config import Config
from ...services.linear_service import LinearService
from ...services.supabase_service import SupabaseService
from ...services.notion_service import NotionService
from .chat_history import ChatHistoryService


class ContextManager:
    """Manages context loading for different Slack bot functions with caching."""
    
    def __init__(self):
        """Initialize the context manager with all required services."""
        self.linear_service = LinearService(
            api_key=Config.LINEAR_API_KEY,
            team_name=Config.LINEAR_TEAM_NAME,
            default_assignee=Config.LINEAR_DEFAULT_ASSIGNEE
        )
        self.supabase_service = SupabaseService()
        self.notion_service = NotionService()
        self.chat_history_service = ChatHistoryService()
        
        # Cache settings
        self.base_context_cache = {}
        self.cache_timestamp = 0
        self.cache_ttl = 300  # 5 minutes
    
    def _is_cache_valid(self) -> bool:
        """Check if base context cache is still valid."""
        return (time.time() - self.cache_timestamp) < self.cache_ttl
    
    def _get_base_context(self) -> Dict[str, Any]:
        """Get cached base context or refresh if expired."""
        if self._is_cache_valid():
            return self.base_context_cache
        
        try:
            # Get Linear workspace context
            linear_context = self.linear_service.get_workspace_context()
            
            # Get recent transcripts (last 7 days)
            end_date = datetime.now().isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            recent_transcripts = self.supabase_service.get_filtered_transcripts_by_date_range(
                start_date, end_date
            )
            
            # Get team member information
            team_members = self._get_team_member_info(linear_context)
            
            context = {
                "linear_workspace": {
                    "projects": [self._format_project(p) for p in linear_context.projects],
                    "milestones": [self._format_milestone(m) for m in linear_context.milestones],
                    "active_issues": [self._format_issue(i) for i in linear_context.issues if i.state_type != 'completed'],
                    "completed_issues": [self._format_issue(i) for i in linear_context.issues if i.state_type == 'completed']
                },
                "recent_transcripts": [
                    {
                        "id": t.get('id'),
                        "meeting_date": t.get('meeting_date'),
                        "participants": t.get('participants', []),
                        "project_tags": t.get('project_tags', []),
                        "filtered_content": t.get('filtered_content', '')[:500] + "..." if len(t.get('filtered_content', '')) > 500 else t.get('filtered_content', '')
                    }
                    for t in recent_transcripts[:5]  # Last 5 transcripts
                ],
                "team_members": team_members,
                "context_timestamp": datetime.now().isoformat()
            }
            
            self.base_context_cache = context
            self.cache_timestamp = time.time()
            
            return context
            
        except Exception as e:
            print(f"Error loading base context: {e}")
            return {"error": f"Failed to load context: {str(e)}"}
    
    def _get_team_member_info(self, linear_context) -> List[Dict[str, Any]]:
        """Extract team member information from Linear context."""
        team_members = {}
        
        # Collect assignees from issues
        for issue in linear_context.issues:
            if issue.assignee_name:
                if issue.assignee_name not in team_members:
                    team_members[issue.assignee_name] = {
                        "name": issue.assignee_name,
                        "active_issues": [],
                        "completed_issues": []
                    }
                
                if issue.state_type == 'completed':
                    team_members[issue.assignee_name]["completed_issues"].append({
                        "title": issue.title,
                        "project": issue.project_name,
                        "state": issue.state_name
                    })
                else:
                    team_members[issue.assignee_name]["active_issues"].append({
                        "title": issue.title,
                        "project": issue.project_name,
                        "state": issue.state_name,
                        "priority": issue.priority
                    })
        
        return list(team_members.values())
    
    def _format_project(self, project) -> Dict[str, Any]:
        """Format Linear project for context."""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "state": project.state,
            "progress": project.progress,
            "target_date": project.target_date,
            "teams": project.teams
        }
    
    def _format_milestone(self, milestone) -> Dict[str, Any]:
        """Format Linear milestone for context."""
        return {
            "id": milestone.id,
            "name": milestone.name,
            "description": milestone.description,
            "target_date": milestone.target_date,
            "project_name": milestone.project_name
        }
    
    def _format_issue(self, issue) -> Dict[str, Any]:
        """Format Linear issue for context."""
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "state": issue.state_name,
            "priority": issue.priority,
            "assignee": issue.assignee_name,
            "project": issue.project_name,
            "milestone": issue.milestone_name,
            "estimate": issue.estimate
        }
    
    def get_chat_context(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Get context for chat function."""
        base_context = self._get_base_context()
        
        # Add conversation history
        conversation_history = self.chat_history_service.get_session_info(user_id, channel_id)
        
        return {
            **base_context,
            "conversation_history": conversation_history,
            "function": "chat"
        }
    
    def get_meeting_summary_context(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Get context for meeting summary function."""
        base_context = self._get_base_context()
        
        # Find specific meeting if timestamp provided
        specific_meeting = None
        if timestamp:
            # Parse timestamp and find matching meeting
            for transcript in base_context.get("recent_transcripts", []):
                meeting_date = transcript.get("meeting_date")
                if meeting_date and timestamp in meeting_date:
                    specific_meeting = transcript
                    break
        
        return {
            **base_context,
            "specific_meeting": specific_meeting,
            "function": "summarize_meeting"
        }
    
    def get_client_status_context(self, client_name: str) -> Dict[str, Any]:
        """Get context for client status function."""
        base_context = self._get_base_context()
        
        # Get client-specific data
        client_projects = [
            p for p in base_context.get("linear_workspace", {}).get("projects", [])
            if client_name.lower() in p.get("name", "").lower()
        ]
        
        client_issues = [
            i for i in base_context.get("linear_workspace", {}).get("active_issues", [])
            if any(client_name.lower() in p.get("name", "").lower() for p in base_context.get("linear_workspace", {}).get("projects", []) if p.get("id") == i.get("project_id"))
        ]
        
        # Get Notion documents for client
        notion_docs = self.notion_service.get_client_documents(client_name)
        
        return {
            **base_context,
            "client_name": client_name,
            "client_projects": client_projects,
            "client_issues": client_issues,
            "notion_docs": notion_docs,
            "function": "client_status"
        }
    
    def get_ticket_creation_context(self, description: str) -> Dict[str, Any]:
        """Get context for ticket creation function."""
        base_context = self._get_base_context()
        
        return {
            **base_context,
            "ticket_description": description,
            "function": "create_tickets"
        }
    
    def get_teammember_context(self, member_name: str) -> Dict[str, Any]:
        """Get context for team member function."""
        base_context = self._get_base_context()
        
        # Find specific team member
        member_info = None
        for member in base_context.get("team_members", []):
            if member_name.lower() in member.get("name", "").lower():
                member_info = member
                break
        
        return {
            **base_context,
            "member_name": member_name,
            "member_info": member_info,
            "function": "teammember"
        }
    
    def get_weekly_summary_context(self) -> Dict[str, Any]:
        """Get context for weekly summary function."""
        base_context = self._get_base_context()
        
        # Get weekly aggregated data
        weekly_data = {
            "meetings_this_week": len(base_context.get("recent_transcripts", [])),
            "active_projects": len([p for p in base_context.get("linear_workspace", {}).get("projects", []) if p.get("state") != "completed"]),
            "active_issues": len(base_context.get("linear_workspace", {}).get("active_issues", [])),
            "completed_issues": len(base_context.get("linear_workspace", {}).get("completed_issues", [])),
            "team_activity": base_context.get("team_members", [])
        }
        
        return {
            **base_context,
            "weekly_data": weekly_data,
            "function": "weekly_summary"
        }
    
    def clear_cache(self) -> None:
        """Clear the base context cache."""
        self.base_context_cache = {}
        self.cache_timestamp = 0 