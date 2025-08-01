"""
Data models for Alpha Machine.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


@dataclass
class LinearProject:
    """Represents a Linear project."""
    id: str
    name: str
    description: Optional[str] = None
    state: Optional[str] = None
    target_date: Optional[str] = None
    progress: Optional[float] = None
    teams: List[str] = field(default_factory=list)


@dataclass
class LinearMilestone:
    """Represents a Linear project milestone."""
    id: str
    name: str
    description: Optional[str] = None
    sort_order: Optional[int] = None
    target_date: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None


@dataclass
class LinearIssue:
    """Represents a Linear issue."""
    id: str
    title: str
    description: Optional[str] = None
    state_name: Optional[str] = None
    state_type: Optional[str] = None
    priority: Optional[int] = None
    estimate: Optional[int] = None
    assignee_name: Optional[str] = None
    team_name: Optional[str] = None
    team_key: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    milestone_id: Optional[str] = None
    milestone_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class LinearContext:
    """Represents the current state of a Linear workspace."""
    projects: List[LinearProject] = field(default_factory=list)
    milestones: List[LinearMilestone] = field(default_factory=list)
    issues: List[LinearIssue] = field(default_factory=list)
    
    def format_for_prompt(self) -> str:
        """Format the context for use in AI prompts."""
        lines = []
        lines.append("CURRENT LINEAR WORKSPACE STATE:")
        lines.append("=" * 50)
        
        for project in self.projects:
            lines.append(f"\nPROJECT: {project.name}")
            lines.append(f"  ID: {project.id}")
            lines.append(f"  State: {project.state or 'Unknown'}")
            lines.append(f"  Progress: {project.progress or 0:.1f}%")
            
            if project.teams:
                lines.append(f"  Teams: {', '.join(project.teams)}")
            
            if project.target_date:
                lines.append(f"  Target Date: {project.target_date}")
            
            if project.description:
                lines.append(f"  Description: {project.description}")
            
            # Find milestones for this project
            project_milestones = [m for m in self.milestones if m.project_id == project.id]
            if project_milestones:
                lines.append("  MILESTONES:")
                for milestone in project_milestones:
                    lines.append(f"    - {milestone.name}")
                    if milestone.description:
                        lines.append(f"      Description: {milestone.description}")
                    if milestone.target_date:
                        lines.append(f"      Target Date: {milestone.target_date}")
            
            # Find issues for this project
            project_issues = [issue for issue in self.issues if issue.project_id == project.id]
            if project_issues:
                active_issues = [issue for issue in project_issues if issue.state_type != 'completed']
                completed_issues = [issue for issue in project_issues if issue.state_type == 'completed']
                
                if active_issues:
                    lines.append("  ACTIVE ISSUES:")
                    for issue in active_issues:
                        lines.append(f"    - {issue.title}")
                        lines.append(f"      State: {issue.state_name or 'Unknown'}")
                        lines.append(f"      Priority: {issue.priority or 'No priority'}")
                        if issue.assignee_name:
                            lines.append(f"      Assignee: {issue.assignee_name}")
                        if issue.milestone_name:
                            lines.append(f"      Milestone: {issue.milestone_name}")
                        if issue.estimate:
                            lines.append(f"      Estimate: {issue.estimate} points")
                        if issue.description:
                            lines.append(f"      Description: {issue.description[:200]}...")
                
                if completed_issues:
                    lines.append("  COMPLETED ISSUES:")
                    for issue in completed_issues[-5:]:  # Show last 5 completed
                        lines.append(f"    - {issue.title}")
                        lines.append(f"      State: {issue.state_name or 'Unknown'}")
                        if issue.assignee_name:
                            lines.append(f"      Assignee: {issue.assignee_name}")
                        if issue.milestone_name:
                            lines.append(f"      Milestone: {issue.milestone_name}")
                        if issue.description:
                            lines.append(f"      Description: {issue.description[:200]}...")
        
        return "\n".join(lines)


class GeneratedIssue(BaseModel):
    """Represents an issue generated by the AI."""
    team: Optional[str] = Field(None, description="Team name")
    project: Optional[str] = Field(None, description="Project name this issue belongs to")
    milestone: Optional[str] = Field(None, description="Milestone name")
    issue_title: str = Field(..., description="Title of the issue")
    issue_description: str = Field(..., description="Detailed description of the issue")
    assign_team_member: Optional[str] = Field(None, description="Email of team member to assign. Leave null if unassigned.")
    time_estimate: Optional[str] = Field(None, description="Time estimate (0.5|1|2|4|8)")
    subissues: Optional[List[str]] = Field(None, description="List of subtasks")
    priority: str = Field(default="2", description="Priority level (0|1|2|3|4, 0=highest, 4=lowest)")
    deadline: Optional[str] = Field(None, description="Deadline date in YYYY-MM-DD format")
    status: str = Field(default="backlog", description="Issue status")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()


class GeneratedIssuesResponse(BaseModel):
    """Response model for AI-generated issues."""
    issues: List[GeneratedIssue] = Field(..., description="List of generated issues")


@dataclass
class ProcessingResult:
    """Represents the result of processing a transcript."""
    generated_issues: List[GeneratedIssue]
    linear_context: LinearContext
    raw_ai_response: str
    processing_time: float
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_issues": [issue.to_dict() for issue in self.generated_issues],
            "processing_time": self.processing_time,
            "success": self.success,
            "error_message": self.error_message,
            "raw_ai_response": self.raw_ai_response
        }


@dataclass
class FilteredTranscript:
    """Represents a filtered transcript stored in Supabase."""
    original_filename: str
    filtered_content: str
    original_length: int
    filtered_length: int
    redaction_count: int
    id: Optional[str] = None
    meeting_date: Optional[datetime] = None
    participants: List[str] = field(default_factory=list)
    project_tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Supabase storage."""
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "filtered_content": self.filtered_content,
            "original_length": self.original_length,
            "filtered_length": self.filtered_length,
            "redaction_count": self.redaction_count,
            "meeting_date": self.meeting_date.isoformat() if self.meeting_date else None,
            "participants": self.participants,
            "project_tags": self.project_tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class TranscriptFilteringResult:
    """Represents the result of filtering a transcript."""
    original_transcript: str
    filtered_transcript: str
    redaction_count: int
    processing_time: float
    success: bool = True
    error_message: Optional[str] = None
    supabase_id: Optional[str] = None  # ID from Supabase after storing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "original_length": len(self.original_transcript),
            "filtered_length": len(self.filtered_transcript),
            "redaction_count": self.redaction_count,
            "processing_time": self.processing_time,
            "success": self.success,
            "error_message": self.error_message,
            "supabase_id": self.supabase_id
        } 