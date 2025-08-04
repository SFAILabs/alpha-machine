"""
Linear API service for managing projects, issues, and workspace data.
"""

import requests
from typing import List, Optional, Dict, Any
from shared.core.models import LinearProject, LinearMilestone, LinearIssue, LinearContext
from shared.core.config import Config


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
            state = issue_data.get('state', {}) or {}
            assignee = issue_data.get('assignee') or {}
            team = issue_data.get('team') or {}
            project = issue_data.get('project') or {}
            milestone = issue_data.get('projectMilestone') or {}
            
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
    
    def get_team_id(self, team_name: str) -> Optional[str]:
        """Get team ID by name."""
        query = """
        query Teams {
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
                if team['name'] == team_name:
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
    
    def get_milestone_id(self, milestone_name: str) -> Optional[str]:
        """Get milestone ID by name."""
        query = """
        query {
            projectMilestones {
                nodes {
                    id
                    name
                    project {
                        name
                    }
                }
            }
        }
        """
        
        try:
            data = self._make_request(query)
            milestones = data['data']['projectMilestones']['nodes']
            for milestone in milestones:
                if milestone['name'] == milestone_name:
                    return milestone['id']
            return None
        except Exception as e:
            print(f"Error getting milestone ID: {e}")
            return None
    
    def create_milestone(self, milestone_name: str, project_id: str, description: str = "") -> Optional[str]:
        """Create a new milestone in test mode."""
        if not Config.LINEAR_TEST_MODE:
            raise ValueError(
                "🚨 CRITICAL SAFETY ERROR: Attempting to create milestone in production. "
                "Set LINEAR_TEST_MODE=true in your .env file to enable writing."
            )

        print(f"✅ SAFETY CHECK PASSED: Creating milestone in test mode.")
        
        milestone_name = f"[TEST] {milestone_name}"

        mutation = """
        mutation CreateProjectMilestone($input: ProjectMilestoneCreateInput!) {
            projectMilestoneCreate(input: $input) {
                success
                projectMilestone {
                    id
                    name
                    description
                }
            }
        }
        """
        
        variables = {
            "input": {
                "name": milestone_name,
                "description": description,
                "projectId": project_id
            }
        }
        
        try:
            result = self._make_request(mutation, variables)
            if result.get('data', {}).get('projectMilestoneCreate', {}).get('success'):
                return result['data']['projectMilestoneCreate']['projectMilestone']['id']
            else:
                print(f"Error creating milestone: {result}")
                return None
        except Exception as e:
            print(f"Error creating milestone: {e}")
            return None
    
    def get_or_create_milestone(self, milestone_name: str, project_id: str, description: str = "") -> Optional[str]:
        """Get existing milestone ID or create new milestone."""
        # First try to get existing milestone
        milestone_id = self.get_milestone_id(milestone_name)
        if milestone_id:
            return milestone_id
        
        # Create new milestone if not found
        return self.create_milestone(milestone_name, project_id, description)
    
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
        """Create a new project in test mode."""
        if not Config.LINEAR_TEST_MODE:
            raise ValueError(
                "🚨 CRITICAL SAFETY ERROR: Attempting to create project in production. "
                "Set LINEAR_TEST_MODE=true in your .env file to enable writing."
            )

        print(f"✅ SAFETY CHECK PASSED: Creating project in test mode.")
        
        project_name = f"[TEST] {project_name}"
        
        team_id = self.get_team_id(self.team_name)
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
        """Create a new issue in test mode."""
        if not Config.LINEAR_TEST_MODE:
            raise ValueError(
                "🚨 CRITICAL SAFETY ERROR: Attempting to write to production. "
                "Set LINEAR_TEST_MODE=true in your .env file to enable writing."
            )

        print(f"✅ SAFETY CHECK PASSED: Writing to workspace in test mode.")

        # Prefix title with [TEST] in test mode
        issue_data['issue_title'] = f"[TEST] {issue_data['issue_title']}"
        
        team_name_to_find = issue_data.get('team') or self.team_name
        team_id = self.get_team_id(team_name_to_find)

        assignee_id = None
        if issue_data.get('assign_team_member'):
            assignee_id = self.get_user_id(issue_data['assign_team_member'])
        
        if not team_id:
            print(f"Error: Team '{team_name_to_find}' not found")
            return None
        
        # Get or create project
        project_id = None
        if issue_data.get('project'):
            print(f"   📁 Getting/creating project: {issue_data['project']}")
            project_id = self.get_or_create_project(issue_data['project'])
            if project_id:
                print(f"   ✅ Project ID: {project_id}")
            else:
                print(f"   ❌ Failed to get/create project: {issue_data['project']}")
        
        # Get or create milestone
        milestone_id = None
        if issue_data.get('milestone') and project_id:
            print(f"   🎯 Getting/creating milestone: {issue_data['milestone']}")
            milestone_id = self.get_or_create_milestone(issue_data['milestone'], project_id)
            if milestone_id:
                print(f"   ✅ Milestone ID: {milestone_id}")
            else:
                print(f"   ❌ Failed to get/create milestone: {issue_data['milestone']}")
        elif issue_data.get('milestone') and not project_id:
            print(f"   ⚠️  Skipping milestone creation - no project ID available")
        
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
                "priority": priority,
                "estimate": estimate
            }
        }
        
        # Add due date if provided
        if issue_data.get('deadline'):
            variables["input"]["dueDate"] = issue_data['deadline']
        
        # Add assignee if found
        if assignee_id:
            variables["input"]["assigneeId"] = assignee_id
        
        # Add project if available
        if project_id:
            variables["input"]["projectId"] = project_id
        
        # Add milestone if available
        if milestone_id:
            variables["input"]["projectMilestoneId"] = milestone_id
        
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
        """Delete an issue by ID in test mode."""
        if not Config.LINEAR_TEST_MODE:
            raise ValueError(
                "🚨 CRITICAL SAFETY ERROR: Attempting to delete issue in production. "
                "Set LINEAR_TEST_MODE=true in your .env file to enable writing."
            )

        print(f"✅ SAFETY CHECK PASSED: Deleting issue in test mode.")

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