#!/usr/bin/env python3
"""
Script to create a structured project view: Projects -> Milestones -> Issues.
"""

import json
import requests
from config import Config

def fetch_linear_data():
    """Fetch projects, projectMilestones, and issues from Linear."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": Config.LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
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
    response = requests.post(url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Linear API request failed: {response.status_code} - {response.text}")

def organize_data(data):
    """Organize data into structured project view with projectMilestones."""
    if 'data' not in data:
        return {}
    projects = data['data'].get('projects', {}).get('nodes', [])
    milestones = data['data'].get('projectMilestones', {}).get('nodes', [])
    issues = data['data'].get('issues', {}).get('nodes', [])
    structured_view = {}
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', 'Unknown Project')
        project_data = {
            'id': project_id,
            'description': project.get('description'),
            'state': project.get('state'),
            'target_date': project.get('targetDate'),
            'progress': project.get('progress', 0),
            'teams': [team.get('name') for team in (project.get('teams', {}).get('nodes', []) or [])],
            'milestones': {},
            'issues': []
        }
        # Find issues for this project
        project_issues = [issue for issue in issues if (issue.get('project') or {}).get('id') == project_id]
        project_data['issues'] = project_issues
        # Find milestones for this project
        project_milestones = [m for m in milestones if (m.get('project') or {}).get('id') == project_id]
        for milestone in project_milestones:
            milestone_id = milestone.get('id')
            milestone_name = milestone.get('name', 'Unknown Milestone')
            milestone_data = {
                'id': milestone_id,
                'description': milestone.get('description'),
                'sortOrder': milestone.get('sortOrder'),
                'targetDate': milestone.get('targetDate'),
                'issues': []
            }
            # Find issues for this milestone
            milestone_issues = [issue for issue in project_issues if (issue.get('projectMilestone') or {}).get('id') == milestone_id]
            milestone_data['issues'] = milestone_issues
            project_data['milestones'][milestone_name] = milestone_data
        structured_view[project_name] = project_data
    return structured_view

def print_structured_view(structured_view):
    """Print the structured view in a readable format."""
    print("=" * 80)
    print("STRUCTURED PROJECT VIEW")
    print("=" * 80)
    
    for project_name, project_data in structured_view.items():
        print(f"\n📁 PROJECT: {project_name}")
        print(f"   State: {project_data.get('state', 'Unknown')}")
        print(f"   Progress: {project_data.get('progress', 0):.1f}%")
        print(f"   Teams: {', '.join(project_data.get('teams', []))}")
        if project_data.get('target_date'):
            print(f"   Target Date: {project_data['target_date']}")
        if project_data.get('description'):
            print(f"   Description: {project_data['description']}")
        
        # Show milestones
        milestones = project_data.get('milestones', {})
        if milestones:
            print(f"\n   📋 MILESTONES:")
            for milestone_name, milestone_data in milestones.items():
                print(f"\n      🎯 {milestone_name} (Cycle #N/A)")
                print(f"         Period: {milestone_data.get('starts_at', 'N/A')} to {milestone_data.get('ends_at', 'N/A')}")
                if milestone_data.get('description'):
                    print(f"         Description: {milestone_data['description']}")
                
                # Separate active and completed issues
                milestone_issues = milestone_data.get('issues', [])
                active_issues = [issue for issue in milestone_issues 
                               if (issue.get('state') or {}).get('type') != 'completed']
                completed_issues = [issue for issue in milestone_issues 
                                  if (issue.get('state') or {}).get('type') == 'completed']
                
                if active_issues:
                    print(f"\n         🔄 ACTIVE ISSUES ({len(active_issues)}):")
                    for issue in active_issues:
                        state = issue.get('state') or {}
                        assignee = issue.get('assignee') or {}
                        print(f"            • {issue.get('title', 'No title')}")
                        print(f"              State: {state.get('name', 'Unknown')}")
                        print(f"              Priority: {issue.get('priority', 'No priority')}")
                        if assignee.get('name'):
                            print(f"              Assignee: {assignee['name']}")
                        if issue.get('estimate'):
                            print(f"              Estimate: {issue['estimate']} points")
                        if issue.get('description'):
                            print(f"              Description: {issue['description'][:100]}...")
                
                if completed_issues:
                    print(f"\n         ✅ COMPLETED ISSUES ({len(completed_issues)}):")
                    for issue in completed_issues:
                        state = issue.get('state') or {}
                        assignee = issue.get('assignee') or {}
                        print(f"            • {issue.get('title', 'No title')}")
                        print(f"              State: {state.get('name', 'Unknown')}")
                        if assignee.get('name'):
                            print(f"              Assignee: {assignee['name']}")
                        if issue.get('description'):
                            print(f"              Description: {issue['description'][:100]}...")
        else:
            print(f"\n   📋 MILESTONES: None found")
        
        # Show issues not in any milestone
        project_issues = project_data.get('issues', [])
        unmilestoned_issues = [issue for issue in project_issues 
                             if not (issue.get('projectMilestone') or {}).get('name')]
        
        if unmilestoned_issues:
            active_unmilestoned = [issue for issue in unmilestoned_issues 
                                 if (issue.get('state') or {}).get('type') != 'completed']
            completed_unmilestoned = [issue for issue in unmilestoned_issues 
                                    if (issue.get('state') or {}).get('type') == 'completed']
            
            print(f"\n   📝 ISSUES WITHOUT MILESTONE:")
            if active_unmilestoned:
                print(f"\n      🔄 ACTIVE ({len(active_unmilestoned)}):")
                for issue in active_unmilestoned:
                    state = issue.get('state') or {}
                    assignee = issue.get('assignee') or {}
                    print(f"         • {issue.get('title', 'No title')}")
                    print(f"           State: {state.get('name', 'Unknown')}")
                    if assignee.get('name'):
                        print(f"           Assignee: {assignee['name']}")
                    if issue.get('description'):
                        print(f"           Description: {issue['description'][:100]}...")
            
            if completed_unmilestoned:
                print(f"\n      ✅ COMPLETED ({len(completed_unmilestoned)}):")
                for issue in completed_unmilestoned:
                    state = issue.get('state') or {}
                    assignee = issue.get('assignee') or {}
                    print(f"         • {issue.get('title', 'No title')}")
                    print(f"           State: {state.get('name', 'Unknown')}")
                    if assignee.get('name'):
                        print(f"           Assignee: {assignee['name']}")
                    if issue.get('description'):
                        print(f"           Description: {issue['description'][:100]}...")
        
        print("\n" + "-" * 80)

def main():
    """Main function to create structured project view."""
    try:
        if not Config.LINEAR_API_KEY:
            print("Error: LINEAR_API_KEY environment variable is required")
            return 1
        
        print("Fetching Linear data for structured project view...")
        
        data = fetch_linear_data()
        structured_view = organize_data(data)
        
        print_structured_view(structured_view)
        
        # Save structured view to file
        output_file = "structured_project_view.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_view, f, indent=2)
        
        print(f"\nStructured view saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 