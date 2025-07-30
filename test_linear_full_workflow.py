#!/usr/bin/env python3
"""
Script to test creating a project, milestone, and issue in sequence using TEST_LINEAR_API_KEY.
"""

import json
import requests
from config import Config

def get_team_id(api_key, team_name="Jonathan Test Space"):
    """Get team ID by name."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
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
    
    response = requests.post(url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        teams = data['data']['teams']['nodes']
        for team in teams:
            if team['name'] == team_name:
                return team['id']
    return None

def get_user_id(api_key, user_email):
    """Get user ID by email."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
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
    
    response = requests.post(url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        users = data['data']['users']['nodes']
        for user in users:
            if user['email'] == user_email:
                return user['id']
    return None

def create_project(api_key, project_data):
    """Create a new project in Linear."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    # Get team ID
    team_id = get_team_id(api_key, project_data['team'])
    if not team_id:
        print(f"Error: Team '{project_data['team']}' not found")
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
                teams {
                    nodes {
                        name
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "input": {
            "name": project_data['name'],
            "description": project_data.get('description', ''),
            "teamIds": [team_id],
            "state": project_data.get('state', 'backlog')
        }
    }
    
    response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('data', {}).get('projectCreate', {}).get('success'):
            return result['data']['projectCreate']['project']
        else:
            print(f"Error creating project: {result}")
            return None
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def create_milestone(api_key, milestone_data):
    """Create a new milestone in Linear."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    mutation = """
    mutation CreateProjectMilestone($input: ProjectMilestoneCreateInput!) {
        projectMilestoneCreate(input: $input) {
            success
            projectMilestone {
                id
                name
                description
                project {
                    id
                    name
                }
            }
        }
    }
    """
    
    variables = {
        "input": {
            "name": milestone_data['name'],
            "description": milestone_data.get('description', ''),
            "projectId": milestone_data['project_id']
        }
    }
    
    response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('data', {}).get('projectMilestoneCreate', {}).get('success'):
            return result['data']['projectMilestoneCreate']['projectMilestone']
        else:
            print(f"Error creating milestone: {result}")
            return None
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def create_issue(api_key, issue_data):
    """Create a new issue in Linear."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    # Get required IDs
    team_id = get_team_id(api_key, issue_data['team'])
    assignee_id = get_user_id(api_key, issue_data['assign_team_member'])
    
    if not team_id:
        print(f"Error: Team '{issue_data['team']}' not found")
        return None
    if not assignee_id:
        print(f"Error: User '{issue_data['assign_team_member']}' not found")
        return None
    
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
                projectMilestone {
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
    
    # Add optional fields only if they exist
    if issue_data.get('project_id'):
        variables["input"]["projectId"] = issue_data['project_id']
    if issue_data.get('milestone_id'):
        variables["input"]["projectMilestoneId"] = issue_data['milestone_id']
    
    response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('data', {}).get('issueCreate', {}).get('success'):
            return result['data']['issueCreate']['issue']
        else:
            print(f"Error creating issue: {result}")
            return None
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def test_full_workflow():
    """Test creating project, milestone, and issue in sequence."""
    if not Config.TEST_LINEAR_API_KEY:
        print("Error: TEST_LINEAR_API_KEY environment variable is required")
        return 1
    
    print("Testing full Linear workflow: Project → Milestone → Issue")
    print(f"Using TEST_LINEAR_API_KEY: {Config.TEST_LINEAR_API_KEY[:10]}...")
    
    # Step 1: Create Project
    print("\n=== STEP 1: Creating Project ===")
    project_data = {
        "team": "Jonathan Test Space",
        "name": "AI Ticket Generation Test",
        "description": "A test project to verify the full Linear API workflow including project, milestone, and issue creation.",
        "state": "started"
    }
    
    project = create_project(Config.TEST_LINEAR_API_KEY, project_data)
    if not project:
        print("❌ Failed to create project")
        return 1
    
    print(f"✅ Project created: {project['name']} (ID: {project['id']})")
    
    # Step 2: Create Milestone
    print("\n=== STEP 2: Creating Milestone ===")
    milestone_data = {
        "name": "Initial Setup",
        "description": "Initial setup and testing phase for the AI ticket generation system.",
        "project_id": project['id']
    }
    
    milestone = create_milestone(Config.TEST_LINEAR_API_KEY, milestone_data)
    if not milestone:
        print("❌ Failed to create milestone")
        return 1
    
    print(f"✅ Milestone created: {milestone['name']} (ID: {milestone['id']})")
    
    # Step 3: Create Issue
    print("\n=== STEP 3: Creating Issue ===")
    issue_data = {
        "team": "Jonathan Test Space",
        "project_id": project['id'],
        "milestone_id": milestone['id'],
        "issue_title": "Test Issue - Full Workflow",
        "issue_description": "This issue was created as part of testing the full Linear API workflow (project → milestone → issue).\n\nAcceptance Criteria:\n- Project created successfully\n- Milestone created and linked to project\n- Issue created and linked to both project and milestone\n- All relationships working correctly",
        "assign_team_member": "jonny34923@gmail.com",
        "time_estimate": "3",
        "priority": "1",
        "status": "backlog"
    }
    
    issue = create_issue(Config.TEST_LINEAR_API_KEY, issue_data)
    if not issue:
        print("❌ Failed to create issue")
        return 1
    
    print(f"✅ Issue created: {issue['title']} (ID: {issue['id']})")
    
    # Summary
    print("\n=== WORKFLOW SUMMARY ===")
    print(f"✅ Project: {project['name']} (ID: {project['id']})")
    print(f"✅ Milestone: {milestone['name']} (ID: {milestone['id']})")
    print(f"✅ Issue: {issue['title']} (ID: {issue['id']})")
    print(f"✅ Assignee: {issue['assignee']['name']} ({issue['assignee']['email']})")
    print(f"✅ Team: {issue['team']['name']}")
    if issue.get('project'):
        print(f"✅ Project: {issue['project']['name']}")
    if issue.get('projectMilestone'):
        print(f"✅ Milestone: {issue['projectMilestone']['name']}")
    print(f"✅ Priority: {issue['priority']}")
    print(f"✅ Estimate: {issue['estimate']} points")
    
    print("\n🎉 Full workflow test completed successfully!")
    return 0

def main():
    """Main function to test full Linear workflow."""
    try:
        return test_full_workflow()
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 