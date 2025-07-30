"""
Utility functions for Alpha Machine.
"""

import json
from pathlib import Path
from typing import Dict, Any, List


def save_json(data: Dict[str, Any], file_path: Path, indent: int = 2) -> None:
    """Save data to JSON file with error handling."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")
        raise


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load data from JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {file_path}: {e}")
        raise
    except Exception as e:
        print(f"Error loading JSON from {file_path}: {e}")
        raise


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def print_separator(title: str = "", char: str = "=", width: int = 50) -> None:
    """Print a formatted separator with optional title."""
    if title:
        padding = (width - len(title) - 2) // 2
        print(f"{char * padding} {title} {char * padding}")
    else:
        print(char * width)


def print_issue_summary(issues: List[Dict[str, Any]], title: str = "ISSUES") -> None:
    """Print a formatted summary of issues."""
    print_separator(title)
    
    if not issues:
        print("No issues found.")
        return
    
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. {issue.get('issue_title', 'No title')}")
        description = issue.get('issue_description', '')
        if description:
            print(f"   Description: {description[:100]}{'...' if len(description) > 100 else ''}")
        print(f"   Project: {issue.get('project', 'No project')}")
        print(f"   Priority: {issue.get('priority', 'No priority')}")
        print(f"   Estimate: {issue.get('time_estimate', 'No estimate')} points")
        print(f"   Assignee: {issue.get('assign_team_member', 'No assignee')}")


def validate_required_files(*file_paths: Path) -> bool:
    """Validate that all required files exist."""
    missing_files = []
    
    for file_path in file_paths:
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print("Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True


def create_directory_if_not_exists(directory: Path) -> None:
    """Create directory if it doesn't exist."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory {directory}: {e}")
        raise 