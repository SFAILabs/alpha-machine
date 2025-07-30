#!/usr/bin/env python3
"""
Script to process meeting transcripts and generate structured tickets using GPT-4o-mini.
"""

import yaml
import json
import requests
from pathlib import Path
from openai import OpenAI
from config import Config

def load_prompts(prompts_file: str = "src/prompts.yml") -> dict:
    """Load prompts from YAML file."""
    with open(prompts_file, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def load_transcript(transcript_file: str = "sfai_dev_standup_transcript.txt") -> str:
    """Load transcript from text file."""
    with open(transcript_file, 'r', encoding='utf-8') as file:
        return file.read()

def fetch_linear_context():
    """Fetch Linear data and format it for context."""
    if not Config.LINEAR_API_KEY:
        print("Warning: LINEAR_API_KEY not set, skipping Linear context")
        return "No Linear context available - LINEAR_API_KEY not configured"
    
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": Config.LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Query to get projects, projectMilestones, and issues
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
        response = requests.post(url, json={"query": query}, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Warning: Linear API request failed: {response.status_code}")
            return "Linear context unavailable - API request failed"
    except Exception as e:
        print(f"Warning: Error fetching Linear data: {e}")
        return "Linear context unavailable - connection error"

def format_linear_context(linear_data):
    """Format Linear data into a readable context string."""
    if isinstance(linear_data, str):
        return linear_data
    
    if 'data' not in linear_data:
        return "Linear context unavailable - invalid data structure"
    
    projects = linear_data['data'].get('projects', {}).get('nodes', [])
    milestones = linear_data['data'].get('projectMilestones', {}).get('nodes', [])
    issues = linear_data['data'].get('issues', {}).get('nodes', [])
    
    context_lines = []
    context_lines.append("CURRENT LINEAR WORKSPACE STATE:")
    context_lines.append("=" * 50)
    
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name', 'Unknown Project')
        
        context_lines.append(f"\nPROJECT: {project_name}")
        context_lines.append(f"  ID: {project_id}")
        context_lines.append(f"  State: {project.get('state', 'Unknown')}")
        context_lines.append(f"  Progress: {project.get('progress', 0):.1f}%")
        
        teams = [team.get('name') for team in (project.get('teams', {}).get('nodes', []) or [])]
        if teams:
            context_lines.append(f"  Teams: {', '.join(teams)}")
        
        if project.get('targetDate'):
            context_lines.append(f"  Target Date: {project['targetDate']}")
        
        if project.get('description'):
            context_lines.append(f"  Description: {project['description']}")
        
        # Find milestones for this project
        project_milestones = [m for m in milestones if (m.get('project') or {}).get('id') == project_id]
        if project_milestones:
            context_lines.append("  MILESTONES:")
            for milestone in project_milestones:
                milestone_name = milestone.get('name', 'Unknown Milestone')
                context_lines.append(f"    - {milestone_name}")
                if milestone.get('description'):
                    context_lines.append(f"      Description: {milestone['description']}")
                if milestone.get('targetDate'):
                    context_lines.append(f"      Target Date: {milestone['targetDate']}")
        
        # Find issues for this project
        project_issues = [issue for issue in issues if (issue.get('project') or {}).get('id') == project_id]
        if project_issues:
            active_issues = [issue for issue in project_issues if (issue.get('state') or {}).get('type') != 'completed']
            completed_issues = [issue for issue in project_issues if (issue.get('state') or {}).get('type') == 'completed']
            
            if active_issues:
                context_lines.append("  ACTIVE ISSUES:")
                for issue in active_issues:
                    state = issue.get('state') or {}
                    assignee = issue.get('assignee') or {}
                    milestone = issue.get('projectMilestone') or {}
                    
                    context_lines.append(f"    - {issue.get('title', 'No title')}")
                    context_lines.append(f"      State: {state.get('name', 'Unknown')}")
                    context_lines.append(f"      Priority: {issue.get('priority', 'No priority')}")
                    if assignee.get('name'):
                        context_lines.append(f"      Assignee: {assignee['name']}")
                    if milestone.get('name'):
                        context_lines.append(f"      Milestone: {milestone['name']}")
                    if issue.get('estimate'):
                        context_lines.append(f"      Estimate: {issue['estimate']} points")
                    if issue.get('description'):
                        context_lines.append(f"      Description: {issue['description'][:200]}...")
            
            if completed_issues:
                context_lines.append("  COMPLETED ISSUES:")
                for issue in completed_issues[-5:]:  # Show last 5 completed
                    state = issue.get('state') or {}
                    assignee = issue.get('assignee') or {}
                    milestone = issue.get('projectMilestone') or {}
                    
                    context_lines.append(f"    - {issue.get('title', 'No title')}")
                    context_lines.append(f"      State: {state.get('name', 'Unknown')}")
                    if assignee.get('name'):
                        context_lines.append(f"      Assignee: {assignee['name']}")
                    if milestone.get('name'):
                        context_lines.append(f"      Milestone: {milestone['name']}")
                    if issue.get('description'):
                        context_lines.append(f"      Description: {issue['description'][:200]}...")
    
    return "\n".join(context_lines)

def format_prompt(prompts: dict, transcript: str, linear_context: str) -> tuple[str, str]:
    """Format the system and user prompts with the transcript and Linear context."""
    prompt_config = prompts.get('transcript_to_linear_tickets', {})
    
    system_prompt = prompt_config.get('system_prompt', '')
    user_prompt_template = prompt_config.get('user_prompt', '')
    
    # Format the user prompt with the transcript and Linear context
    user_prompt = user_prompt_template.format(
        linear_context=linear_context,
        transcription=transcript
    )
    
    return system_prompt, user_prompt

def call_openai(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI API with the formatted prompts."""
    try:
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for more consistent output
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise

def parse_json_response(response: str) -> dict:
    """Parse the JSON response from OpenAI."""
    try:
        # Try to extract JSON from the response (could be object or array)
        start_idx = response.find('[')
        if start_idx == -1:
            start_idx = response.find('{')
        
        if start_idx == -1:
            raise ValueError("No JSON object or array found in response")
        
        # Find the matching closing bracket/brace
        if response[start_idx] == '[':
            # Find matching closing bracket
            bracket_count = 0
            for i, char in enumerate(response[start_idx:], start_idx):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            else:
                raise ValueError("No matching closing bracket found")
        else:
            # Find matching closing brace
            brace_count = 0
            for i, char in enumerate(response[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            else:
                raise ValueError("No matching closing brace found")
        
        json_str = response[start_idx:end_idx]
        parsed_data = json.loads(json_str)
        
        # Return the parsed data as-is (should be an array of issues)
        return parsed_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {response}")
        raise

# Linear API functions for creating issues
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

def create_project_in_test_space(project_name, project_description=""):
    """Create a project in the test Linear workspace."""
    if not Config.TEST_LINEAR_API_KEY:
        print("Warning: TEST_LINEAR_API_KEY not set, skipping project creation")
        return None
    
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": Config.TEST_LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get team ID
    team_id = get_team_id(Config.TEST_LINEAR_API_KEY, "Jonathan Test Space")
    if not team_id:
        print(f"Error: Team 'Jonathan Test Space' not found")
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

def get_or_create_project(project_name, project_description=""):
    """Get existing project or create new one in test space."""
    # First try to get existing project
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": Config.TEST_LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
    
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
    
    response = requests.post(url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        projects = data['data']['projects']['nodes']
        for project in projects:
            if project['name'] == project_name:
                return project['id']
    
    # Create new project if not found
    print(f"Creating new project: {project_name}")
    new_project = create_project_in_test_space(project_name, project_description)
    return new_project['id'] if new_project else None

def create_issue_in_test_space(issue_data):
    """Create a new issue in the test Linear workspace."""
    if not Config.TEST_LINEAR_API_KEY:
        print("Warning: TEST_LINEAR_API_KEY not set, skipping issue creation")
        return None
    
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": Config.TEST_LINEAR_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get required IDs
    team_id = get_team_id(Config.TEST_LINEAR_API_KEY, "Jonathan Test Space")
    assignee_id = get_user_id(Config.TEST_LINEAR_API_KEY, issue_data['assign_team_member'])
    
    if not team_id:
        print(f"Error: Team 'Jonathan Test Space' not found")
        return None
    if not assignee_id:
        print(f"Error: User '{issue_data['assign_team_member']}' not found")
        return None
    
    # Get or create project
    project_id = None
    if issue_data.get('project'):
        project_id = get_or_create_project(issue_data['project'])
    
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

def create_issues_from_ai_output(issues_data):
    """Create Linear issues from AI-generated output."""
    if not isinstance(issues_data, list):
        print("Error: Expected list of issues from AI output")
        return []
    
    created_issues = []
    
    print(f"\nCreating {len(issues_data)} issues in Jonathan Test Space...")
    
    for i, issue_data in enumerate(issues_data, 1):
        # Override assignee to always be jonny34923@gmail.com
        issue_data['assign_team_member'] = 'jonny34923@gmail.com'
        
        print(f"\n--- Creating Issue {i}/{len(issues_data)} ---")
        print(f"Title: {issue_data.get('issue_title', 'No title')}")
        print(f"Project: {issue_data.get('project', 'No project')}")
        print(f"Assignee: {issue_data.get('assign_team_member', 'No assignee')} (overridden)")
        print(f"Priority: {issue_data.get('priority', 'No priority')}")
        print(f"Estimate: {issue_data.get('time_estimate', 'No estimate')} points")
        print(f"Due Date: {issue_data.get('deadline', 'No deadline')}")
        
        created_issue = create_issue_in_test_space(issue_data)
        
        if created_issue:
            print(f"✅ Issue created successfully!")
            print(f"   ID: {created_issue['id']}")
            print(f"   Title: {created_issue['title']}")
            print(f"   Assignee: {created_issue['assignee']['name']}")
            print(f"   Team: {created_issue['team']['name']}")
            if created_issue.get('project'):
                print(f"   Project: {created_issue['project']['name']}")
            if created_issue.get('dueDate'):
                print(f"   Due Date: {created_issue['dueDate']}")
            print(f"   Priority: {created_issue['priority']}")
            print(f"   Estimate: {created_issue['estimate']} points")
            created_issues.append(created_issue)
        else:
            print(f"❌ Failed to create issue")
    
    return created_issues

def main():
    """Main function to process the transcript."""
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize OpenAI client
        openai_config = Config.get_openai_config()
        client = OpenAI(api_key=openai_config['api_key'])
        
        print("Loading prompts and transcript...")
        
        # Load prompts and transcript
        prompts = load_prompts()
        transcript = load_transcript()
        
        print("Fetching Linear context from SFAI workspace...")
        
        # Fetch and format Linear context from SFAI workspace
        linear_data = fetch_linear_context()
        linear_context = format_linear_context(linear_data)
        
        print("Formatting prompts...")
        
        # Format prompts with both transcript and Linear context
        system_prompt, user_prompt = format_prompt(prompts, transcript, linear_context)
        
        print(f"Calling OpenAI API with model: {Config.OPENAI_MODEL}")
        
        # Call OpenAI API
        response = call_openai(client, system_prompt, user_prompt)
        
        print("Parsing response...")
        
        # Parse the JSON response
        result = parse_json_response(response)
        
        print("\n" + "="*50)
        print("GENERATED TICKETS")
        print("="*50)
        
        # Pretty print the result
        print(json.dumps(result, indent=2))
        
        # Save to file
        output_file = "generated_tickets.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        # Create issues in Linear test workspace
        if isinstance(result, list) and len(result) > 0:
            print(f"\n" + "="*50)
            print("CREATING ISSUES IN LINEAR")
            print("="*50)
            
            created_issues = create_issues_from_ai_output(result)
            
            print(f"\n" + "="*50)
            print("SUMMARY")
            print("="*50)
            print(f"AI Generated: {len(result)} issues")
            print(f"Successfully Created: {len(created_issues)} issues")
            print(f"Failed: {len(result) - len(created_issues)} issues")
            
            if created_issues:
                print(f"\nCreated issues in Jonathan Test Space:")
                for issue in created_issues:
                    print(f"  - {issue['title']} (ID: {issue['id']})")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 