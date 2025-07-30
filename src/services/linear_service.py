"""
Linear API service for managing projects, issues, and workspace data.
"""

import requests
from typing import List, Optional, Dict, Any
from ..models import LinearProject, LinearMilestone, LinearIssue, LinearContext
from ..config import Config


class LinearService:
    """Service for interacting with Linear API."""
    
    def __init__(self, api_key: str, team_name: str, default_assignee: str):
        self.api_key = api_key
        self.team_name = team_name
        self.default_assignee = default_assignee
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GraphQL request to Linear API."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(self.base_url, json=payload, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Linear API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_workspace_context(self) -> LinearContext:
        """Fetch and parse the current workspace state."""
        query = """
        query {
            projects {
                nodes {
                    id
                    name
                    description
                    state
                    targetDate
                    progress
                    teams { nodes { name key } }
                }
            }
            projectMilestones {
                nodes {
                    id
                    name
                    description
                    sortOrder
                    targetDate
                    project { id name }
                }
            }
            issues {
                nodes {
                    id
                    title
                    description
                    state { name type }
                    priority
                    estimate
                    assignee { name }
                    team { name key }
                    project { id name }
                    projectMilestone { id name }
                    createdAt
                    updatedAt
                }
            }
        }
        """
        
        try:
            data = self._make_request(query)
            return self._parse_workspace_data(data)
        except Exception as e:
            print(f"Warning: Error fetching Linear data: {e}")
            return LinearContext()
    
    def _parse_workspace_data(self, data: Dict[str, Any]) -> LinearContext:
        """Parse Linear API response into structured data models."""
        if 'data' not in data:
            return LinearContext()
        
        projects = []
        milestones = []
        issues = []
        
        # Parse projects
        for project_data in data['data'].get('projects', {}).get('nodes', []):
            project = LinearProject(
                id=project_data.get('id'),
                name=project_data.get('name', 'Unknown Project'),
                description=project_data.get('description'),
                state=project_data.get('state'),
                target_date=project_data.get('targetDate'),
                progress=project_data.get('progress'),
                teams=[team.get('name') for team in (project_data.get('teams', {}).get('nodes', []) or [])]
            )
            projects.append(project)
        
        # Parse milestones
        for milestone_data in data['data'].get('projectMilestones', {}).get('nodes', []):
            project = milestone_data.get('project', {})
            milestone = LinearMilestone(
                id=milestone_data.get('id'),
                name=milestone_data.get('name', 'Unknown Milestone'),
                description=milestone_data.get('description'),
                sort_order=milestone_data.get('sortOrder'),
                target_date=milestone_data.get('targetDate'),
                project_id=project.get('id'),
                project_name=project.get('name')
            )
            milestones.append(milestone)
        
        # Parse issues
        for issue_data in data['data'].get('issues', {}).get('nodes', []):
            state = issue_data.get('state', {})
            assignee = issue_data.get('assignee', {})
            team = issue_data.get('team', {})
            project = issue_data.get('project', {})
            milestone = issue_data.get('projectMilestone', {})
            
            issue = LinearIssue(
                id=issue_data.get('id'),
                title=issue_data.get('title', 'No title'),
                description=issue_data.get('description'),
                state_name=state.get('name'),
                state_type=state.get('type'),
                priority=issue_data.get('priority'),
                estimate=issue_data.get('estimate'),
                assignee_name=assignee.get('name'),
                team_name=team.get('name'),
                team_key=team.get('key'),
                project_id=project.get('id'),
                project_name=project.get('name'),
                milestone_id=milestone.get('id'),
                milestone_name=milestone.get('name'),
                created_at=issue_data.get('createdAt'),
                updated_at=issue_data.get('updatedAt')
            )
            issues.append(issue)
        
        return LinearContext(projects=projects, milestones=milestones, issues=issues)
    
    def get_team_id(self) -> Optional[str]:
        """Get team ID by name."""
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """
        
        try:
            data = self._make_request(query)
            teams = data['data']['teams']['nodes']
            for team in teams:
                if team['name'] == self.team_name:
                    return team['id']
            return None
        except Exception as e:
            print(f"Error getting team ID: {e}")
            return None
    
    def get_user_id(self, user_email: str) -> Optional[str]:
        """Get user ID by email."""
        query = """
        query {
            users {
                nodes {
                    id
                    email
                    name
                }
            }
        }
        """
        
        try:
            data = self._make_request(query)
            users = data['data']['users']['nodes']
            for user in users:
                if user['email'] == user_email:
                    return user['id']
            return None
        except Exception as e:
            print(f"Error getting user ID: {e}")
            return None
    
    def get_or_create_project(self, project_name: str, project_description: str = "") -> Optional[str]:
        """Get existing project ID or create new project."""
        # First try to get existing project
        query = """
        query {
            projects {
                nodes {
                    id
                    name
                }
            }
        }
        """
        
        try:
            data = self._make_request(query)
            projects = data['data']['projects']['nodes']
            for project in projects:
                if project['name'] == project_name:
                    return project['id']
            
            # Create new project if not found
            return self._create_project(project_name, project_description)
        except Exception as e:
            print(f"Error getting/creating project: {e}")
            return None
    
    def _create_project(self, project_name: str, project_description: str = "") -> Optional[str]:
        """Create a new project."""
        team_id = self.get_team_id()
        if not team_id:
            print(f"Error: Team '{self.team_name}' not found")
            return None
        
        mutation = """
        mutation CreateProject($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                success
                project {
                    id
                    name
                    description
                    state
                }
            }
        }
        """
        
        variables = {
            "input": {
                "name": project_name,
                "description": project_description,
                "teamIds": [team_id],
                "state": "started"
            }
        }
        
        try:
            result = self._make_request(mutation, variables)
            if result.get('data', {}).get('projectCreate', {}).get('success'):
                return result['data']['projectCreate']['project']['id']
            else:
                print(f"Error creating project: {result}")
                return None
        except Exception as e:
            print(f"Error creating project: {e}")
            return None
    
    def create_issue(self, issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new issue."""
        team_id = self.get_team_id()
        assignee_id = self.get_user_id(issue_data['assign_team_member'])
        
        if not team_id:
            print(f"Error: Team '{self.team_name}' not found")
            return None
        if not assignee_id:
            print(f"Error: User '{issue_data['assign_team_member']}' not found")
            return None
        
        # Get or create project
        project_id = None
        if issue_data.get('project'):
            project_id = self.get_or_create_project(issue_data['project'])
        
        # Convert priority to Linear format (0=highest, 4=lowest)
        priority = int(issue_data['priority']) if issue_data['priority'] else 2
        
        # Convert time estimate to Linear estimate (story points)
        estimate = int(float(issue_data['time_estimate'])) if issue_data['time_estimate'] else None
        
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    title
                    description
                    priority
                    estimate
                    dueDate
                    assignee {
                        name
                        email
                    }
                    team {
                        name
                    }
                    project {
                        name
                    }
                }
            }
        }
        """
        
        variables = {
            "input": {
                "title": issue_data['issue_title'],
                "description": issue_data['issue_description'],
                "teamId": team_id,
                "assigneeId": assignee_id,
                "priority": priority,
                "estimate": estimate
            }
        }
        
        # Add due date if provided
        if issue_data.get('deadline'):
            variables["input"]["dueDate"] = issue_data['deadline']
        
        # Add project if available
        if project_id:
            variables["input"]["projectId"] = project_id
        
        try:
            result = self._make_request(mutation, variables)
            if result.get('data', {}).get('issueCreate', {}).get('success'):
                return result['data']['issueCreate']['issue']
            else:
                print(f"Error creating issue: {result}")
                return None
        except Exception as e:
            print(f"Error creating issue: {e}")
            return None
    
    def _delete_issue(self, issue_id: str) -> bool:
        """Delete an issue by ID."""
        mutation = """
        mutation DeleteIssue($id: String!) {
            issueDelete(id: $id) {
                success
            }
        }
        """
        
        variables = {
            "id": issue_id
        }
        
        try:
            result = self._make_request(mutation, variables)
            return result.get('data', {}).get('issueDelete', {}).get('success', False)
        except Exception as e:
            print(f"Error deleting issue {issue_id}: {e}")
            return False 