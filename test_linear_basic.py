#!/usr/bin/env python3
"""
Basic test script for Linear service connection and operations.

This script tests:
1. Linear API connection
2. Workspace context retrieval
3. Basic ticket creation (dry run)
"""

from pathlib import Path

from src.core.config import Config
from src.services.linear_service import LinearService
from src.core.utils import print_separator


def test_linear_connection():
    """Test basic Linear service connection."""
    print_separator("TESTING LINEAR CONNECTION")
    
    try:
        # Check if Linear API key is configured
        if not Config.TEST_LINEAR_API_KEY and not Config.LINEAR_API_KEY:
            print("❌ No Linear API key configured")
            print("   Please set either TEST_LINEAR_API_KEY (recommended) or LINEAR_API_KEY")
            return None
        
        # Initialize Linear service
        # For testing, we'll use TEST_LINEAR_API_KEY to ensure we're working with Jonathan Test Space
        api_key = Config.TEST_LINEAR_API_KEY or Config.LINEAR_API_KEY
        if not Config.TEST_LINEAR_API_KEY:
            print("⚠️  WARNING: TEST_LINEAR_API_KEY not set, using LINEAR_API_KEY")
            print("   This means you're testing with the SFAI workspace!")
        
        linear_service = LinearService(
            api_key=api_key,
            team_name=Config.LINEAR_TEAM_NAME,
            default_assignee=Config.LINEAR_DEFAULT_ASSIGNEE
        )
        
        print("✅ Linear service initialized successfully")
        print(f"   Team: {Config.LINEAR_TEAM_NAME}")
        print(f"   Default assignee: {Config.LINEAR_DEFAULT_ASSIGNEE}")
        print(f"   Using API key: {'TEST_LINEAR_API_KEY' if Config.TEST_LINEAR_API_KEY else 'LINEAR_API_KEY'}")
        
        return linear_service
        
    except Exception as e:
        print(f"❌ Error initializing Linear service: {e}")
        return None


def test_workspace_context(linear_service):
    """Test retrieving Linear workspace context."""
    print_separator("TESTING WORKSPACE CONTEXT")
    
    try:
        print("📊 Fetching Linear workspace context...")
        context = linear_service.get_workspace_context()
        
        print("✅ Workspace context retrieved successfully")
        print(f"   Projects: {len(context.projects)}")
        print(f"   Milestones: {len(context.milestones)}")
        print(f"   Issues: {len(context.issues)}")
        
        # Show project details
        if context.projects:
            print("\n📁 Projects:")
            for project in context.projects[:5]:  # Show first 5
                print(f"   • {project.name}")
                print(f"     ID: {project.id}")
                print(f"     State: {project.state or 'Unknown'}")
                print(f"     Progress: {project.progress or 0:.1f}%")
                if project.target_date:
                    print(f"     Target Date: {project.target_date}")
                print()
        
        # Show recent issues
        if context.issues:
            active_issues = [i for i in context.issues if i.state_type != 'completed']
            print(f"\n🎫 Active Issues ({len(active_issues)}):")
            for issue in active_issues[:5]:  # Show first 5
                print(f"   • {issue.title}")
                print(f"     State: {issue.state_name or 'Unknown'}")
                print(f"     Priority: {issue.priority or 'No priority'}")
                if issue.assignee_name:
                    print(f"     Assignee: {issue.assignee_name}")
                print()
        
        return context
        
    except Exception as e:
        print(f"❌ Error retrieving workspace context: {e}")
        return None


def test_create_sample_ticket(linear_service, dry_run=True):
    """Test creating a sample ticket (dry run by default)."""
    print_separator("TESTING TICKET CREATION")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No ticket will be created")
    else:
        print("⚠️  LIVE MODE - Ticket will be created in Linear")
    
    try:
        # Sample ticket data
        ticket_data = {
            "title": "Test Ticket - Alpha Machine Integration",
            "description": "This is a test ticket created by the Alpha Machine integration to verify the Linear API connection and ticket creation functionality.",
            "priority": 2,
            "estimate": 2,
            "assigneeEmail": Config.LINEAR_DEFAULT_ASSIGNEE,
            "projectId": None,
            "teamId": None,
        }
        
        print("📝 Sample ticket data:")
        print(f"   Title: {ticket_data['title']}")
        print(f"   Description: {ticket_data['description'][:100]}...")
        print(f"   Priority: {ticket_data['priority']}")
        print(f"   Estimate: {ticket_data['estimate']} points")
        print(f"   Assignee: {ticket_data['assigneeEmail']}")
        
        if not dry_run:
            # Create the ticket
            print("\n🎫 Creating ticket in Linear...")
            result = linear_service.create_issue(ticket_data)
            
            if result:
                print("✅ Ticket created successfully!")
                print(f"   Ticket ID: {result.get('id', 'Unknown')}")
                print(f"   Ticket URL: {result.get('url', 'Unknown')}")
                return result
            else:
                print("❌ Failed to create ticket")
                return None
        else:
            print("\n🔍 Would create ticket (dry run)")
            return {"dry_run": True, "data": ticket_data}
        
    except Exception as e:
        print(f"❌ Error testing ticket creation: {e}")
        return None


def main():
    """Run the basic Linear service tests."""
    print("🧪 Testing Linear Service - Basic Operations")
    print("=" * 50)
    
    # Test Linear connection
    linear_service = test_linear_connection()
    if not linear_service:
        return 1
    
    # Test workspace context
    context = test_workspace_context(linear_service)
    if not context:
        return 1
    
    # Test ticket creation (dry run)
    dry_run = True  # Set to False to actually create a ticket
    result = test_create_sample_ticket(linear_service, dry_run)
    
    print_separator("TEST COMPLETED")
    print("✅ Basic Linear service tests completed!")
    
    if dry_run:
        print("\n💡 To create an actual test ticket:")
        print("   1. Set dry_run=False in the test_create_sample_ticket function")
        print("   2. Ensure your LINEAR_API_KEY has write permissions")
        print("   3. Run this script again")
    
    return 0


if __name__ == "__main__":
    exit(main()) 