"""
Main orchestrator for Alpha Machine workflow.
"""

from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from shared.core.config import Config
from shared.core.models import GeneratedIssue
from shared.services.linear_service import LinearService

class IssuesPayload(BaseModel):
    issues: List[GeneratedIssue]

class LinearOrchestrator:
    """Orchestrator for creating Linear issues from structured data."""
    
    def __init__(self):
        """Initialize the orchestrator with the Linear service."""
        self.linear_service = self._create_linear_service()
    
    def _create_linear_service(self) -> LinearService:
        """Create the Linear service for writing to the workspace."""
        config = Config.get_test_linear_config()
        return LinearService(
            api_key=config['api_key'],
            team_name=config['team_name'],
            default_assignee=config['default_assignee']
        )
    
    def create_linear_issues(self, issues: List[GeneratedIssue]) -> Dict[str, Any]:
        """Create Linear issues from a list of generated issue objects."""
        if not issues:
            print("No issues to create")
            return {"success": True, "created_count": 0, "created_issues": []}
        
        created_issue_details = []
        for issue in issues:
            issue_data = issue.to_dict()
            created_issue = self.linear_service.create_issue(issue_data)
            if created_issue:
                created_issue_details.append(created_issue)
            else:
                print(f"Failed to create issue: {issue.issue_title}")

        return {
            "success": True,
            "created_count": len(created_issue_details),
            "created_issues": created_issue_details
        }

linear_router = APIRouter()
orchestrator = LinearOrchestrator()

@linear_router.post("/create-issues")
def create_issues_endpoint(payload: IssuesPayload):
    """Endpoint to create Linear issues from a list of generated issues."""
    result = orchestrator.create_linear_issues(payload.issues)
    return result 