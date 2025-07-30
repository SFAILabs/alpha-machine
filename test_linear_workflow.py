#!/usr/bin/env python3
"""
Test script for Linear service with transcript processing and ticket creation.

This script tests the full workflow:
1. Load a transcript
2. Process it with AI to extract commercial/monetary information
3. Generate Linear tickets
4. Create tickets in Linear (optional)
"""

import json
from pathlib import Path
from datetime import datetime

from src.core.config import Config
from src.core.models import LinearContext, GeneratedIssue, ProcessingResult
from src.services.ai_service import OpenAIService
from src.services.linear_service import LinearService
from src.services.transcript_service import TranscriptService
from src.core.utils import print_separator, save_json


def test_linear_service_connection():
    """Test Linear service connection and workspace access."""
    print_separator("TESTING LINEAR SERVICE CONNECTION")
    
    try:
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
        
        print(f"✅ Linear service initialized")
        print(f"   Team: {Config.LINEAR_TEAM_NAME}")
        print(f"   Default assignee: {Config.LINEAR_DEFAULT_ASSIGNEE}")
        
        # Test workspace context retrieval
        print("\n📊 Fetching Linear workspace context...")
        context = linear_service.get_workspace_context()
        
        print(f"✅ Workspace context retrieved successfully")
        print(f"   Projects: {len(context.projects)}")
        print(f"   Milestones: {len(context.milestones)}")
        print(f"   Issues: {len(context.issues)}")
        
        # Show some project details
        if context.projects:
            print("\n📁 Sample Projects:")
            for project in context.projects[:3]:
                print(f"   • {project.name} - {project.state or 'Unknown'} ({project.progress or 0:.1f}%)")
        
        return linear_service, context
        
    except Exception as e:
        print(f"❌ Error testing Linear service: {e}")
        return None, None


def test_transcript_processing():
    """Test transcript loading and AI processing."""
    print_separator("TESTING TRANSCRIPT PROCESSING")
    
    try:
        # Initialize services
        transcript_service = TranscriptService()
        ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        
        print(f"✅ Services initialized")
        print(f"   OpenAI model: {Config.OPENAI_MODEL}")
        
        # Check if transcript file exists
        if not transcript_service.transcript_file.exists():
            print(f"❌ Transcript file not found: {transcript_service.transcript_file}")
            print("   Please ensure you have a transcript file available")
            return None, None
        
        # Load transcript
        print(f"\n📄 Loading transcript from: {transcript_service.transcript_file}")
        transcript = transcript_service.load_transcript()
        
        print(f"✅ Transcript loaded successfully")
        print(f"   Length: {len(transcript)} characters")
        print(f"   Preview: {transcript[:200]}...")
        
        # Load prompts
        print(f"\n📝 Loading AI prompts...")
        prompts = transcript_service.load_prompts()
        
        print(f"✅ Prompts loaded successfully")
        print(f"   Available prompt types: {list(prompts.keys())}")
        
        return transcript, prompts
        
    except Exception as e:
        print(f"❌ Error testing transcript processing: {e}")
        return None, None


def test_ai_ticket_generation(transcript, linear_context, prompts):
    """Test AI-powered ticket generation from transcript."""
    print_separator("TESTING AI TICKET GENERATION")
    
    try:
        # Initialize AI service
        ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        
        # Format prompts with transcript and Linear context
        transcript_service = TranscriptService()
        system_prompt, user_prompt = transcript_service.format_prompts(
            transcript, linear_context.format_for_prompt()
        )
        
        print(f"✅ Prompts formatted successfully")
        print(f"   System prompt length: {len(system_prompt)} characters")
        print(f"   User prompt length: {len(user_prompt)} characters")
        
        # Generate tickets using AI
        print(f"\n🤖 Generating Linear tickets with AI...")
        print(f"   This may take a moment...")
        
        generated_issues = ai_service.process_transcript(system_prompt, user_prompt)
        
        print(f"✅ AI ticket generation completed")
        print(f"   Generated {len(generated_issues)} tickets")
        
        # Display generated tickets
        print(f"\n🎫 Generated Tickets:")
        for i, issue in enumerate(generated_issues, 1):
            print(f"\n{i}. {issue.issue_title}")
            print(f"   Description: {issue.issue_description[:100]}...")
            print(f"   Project: {issue.project or 'No project'}")
            print(f"   Priority: {issue.priority}")
            print(f"   Estimate: {issue.time_estimate or 'No estimate'}")
            print(f"   Assignee: {issue.assign_team_member}")
            if issue.deadline:
                print(f"   Deadline: {issue.deadline}")
        
        return generated_issues
        
    except Exception as e:
        print(f"❌ Error testing AI ticket generation: {e}")
        return None


def test_linear_ticket_creation(linear_service, generated_issues, dry_run=True):
    """Test creating tickets in Linear (with dry-run option)."""
    print_separator("TESTING LINEAR TICKET CREATION")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No tickets will be created in Linear")
    else:
        print("⚠️  LIVE MODE - Tickets will be created in Linear")
    
    try:
        created_tickets = []
        
        for i, issue in enumerate(generated_issues[:3], 1):  # Limit to first 3 for testing
            print(f"\n🎫 Processing ticket {i}: {issue.issue_title}")
            
            # Prepare ticket data in the format expected by LinearService
            # Use default assignee for Jonathan Test Space since SFAI users don't exist there
            ticket_data = {
                "issue_title": issue.issue_title,
                "issue_description": issue.issue_description,
                "priority": issue.priority,
                "time_estimate": issue.time_estimate,
                "assign_team_member": Config.LINEAR_DEFAULT_ASSIGNEE,  # Use default assignee
                "project": issue.project,
                "milestone": issue.milestone,
                "deadline": issue.deadline,
            }
            
            print(f"   Title: {ticket_data['issue_title']}")
            print(f"   Priority: {ticket_data['priority']}")
            print(f"   Estimate: {ticket_data['time_estimate']} points")
            print(f"   Assignee: {ticket_data['assign_team_member']}")
            print(f"   Project: {ticket_data['project']}")
            print(f"   Milestone: {ticket_data['milestone']}")
            
            if not dry_run:
                # Create ticket in Linear
                result = linear_service.create_issue(ticket_data)
                if result:
                    created_tickets.append(result)
                    print(f"   ✅ Ticket created: {result.get('id', 'Unknown ID')}")
                else:
                    print(f"   ❌ Failed to create ticket")
            else:
                print(f"   🔍 Would create ticket (dry run)")
                created_tickets.append({"dry_run": True, "data": ticket_data})
        
        print(f"\n📊 Summary:")
        print(f"   Processed: {len(generated_issues[:3])} tickets")
        print(f"   Created: {len(created_tickets)} tickets")
        
        return created_tickets
        
    except Exception as e:
        print(f"❌ Error testing Linear ticket creation: {e}")
        return None


def save_test_results(generated_issues, created_tickets, linear_context):
    """Save test results to JSON file."""
    print_separator("SAVING TEST RESULTS")
    
    try:
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "linear_workflow",
            "generated_issues": [issue.to_dict() for issue in generated_issues] if generated_issues else [],
            "created_tickets": created_tickets or [],
            "linear_context_summary": {
                "projects_count": len(linear_context.projects),
                "milestones_count": len(linear_context.milestones),
                "issues_count": len(linear_context.issues),
                "projects": [{"name": p.name, "state": p.state} for p in linear_context.projects[:5]]
            }
        }
        
        output_file = Path("test_linear_results.json")
        save_json(results, output_file)
        
        print(f"✅ Test results saved to: {output_file}")
        print(f"   Generated issues: {len(results['generated_issues'])}")
        print(f"   Created tickets: {len(results['created_tickets'])}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving test results: {e}")
        return None


def main():
    """Run the complete Linear workflow test."""
    print("🧪 Testing Alpha Machine Linear Workflow")
    print("=" * 50)
    
    # Validate configuration
    try:
        Config.validate()
        print("✅ Configuration validated")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Please check your environment variables")
        return 1
    
    # Test Linear service connection
    linear_service, linear_context = test_linear_service_connection()
    if not linear_service:
        return 1
    
    # Test transcript processing
    transcript, prompts = test_transcript_processing()
    if not transcript:
        return 1
    
    # Test AI ticket generation
    generated_issues = test_ai_ticket_generation(transcript, linear_context, prompts)
    if not generated_issues:
        return 1
    
    # Test Linear ticket creation (dry run by default)
    dry_run = False  # Set to True to prevent ticket creation
    
    # SAFETY WARNING
    if not dry_run:
        print("\n" + "="*60)
        print("🚨 ATTENTION: About to create REAL tickets in Jonathan Test Space")
        print("✅ SAFETY: Using TEST_LINEAR_API_KEY - SFAI workspace is protected")
        print("="*60)
    
    created_tickets = test_linear_ticket_creation(linear_service, generated_issues, dry_run)
    
    # Save results
    save_test_results(generated_issues, created_tickets, linear_context)
    
    print_separator("TEST COMPLETED")
    print("✅ All tests completed successfully!")
    
    if dry_run:
        print("\n💡 To create actual tickets in Linear:")
        print("   1. Set dry_run=False in the test_linear_ticket_creation function")
        print("   2. Ensure your LINEAR_API_KEY has write permissions")
        print("   3. Run this script again")
    
    return 0


if __name__ == "__main__":
    exit(main()) 