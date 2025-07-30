"""
Main orchestrator for Alpha Machine workflow.
"""

import json
import time
from typing import List, Dict, Any
from pathlib import Path

from .config import Config
from .models import ProcessingResult, GeneratedIssue, LinearContext
from .services import LinearService, OpenAIService, TranscriptService


class AlphaMachineOrchestrator:
    """Main orchestrator for the Alpha Machine workflow."""
    
    def __init__(self):
        """Initialize the orchestrator with all required services."""
        # Validate configuration
        Config.validate()
        
        # Initialize services
        self.transcript_service = TranscriptService()
        self.openai_service = self._create_openai_service()
        self.linear_service = self._create_linear_service()
        self.test_linear_service = self._create_test_linear_service()
    
    def _create_openai_service(self) -> OpenAIService:
        """Create OpenAI service with configuration."""
        config = Config.get_openai_config()
        return OpenAIService(
            api_key=config['api_key'],
            model=config['model'],
            max_tokens=config['max_tokens'],
            temperature=config['temperature']
        )
    
    def _create_linear_service(self) -> LinearService:
        """Create Linear service for main workspace."""
        config = Config.get_linear_config()
        return LinearService(
            api_key=config['api_key'],
            team_name=config['team_name'],
            default_assignee=config['default_assignee']
        )
    
    def _create_test_linear_service(self) -> LinearService:
        """Create Linear service for test workspace."""
        config = Config.get_test_linear_config()
        return LinearService(
            api_key=config['api_key'],
            team_name=config['team_name'],
            default_assignee=config['default_assignee']
        )
    
    def process_transcript(self, output_file: Path = None) -> ProcessingResult:
        """Main workflow: process transcript and generate Linear issues."""
        start_time = time.time()
        
        try:
            # Validate files
            if not self.transcript_service.validate_files():
                raise FileNotFoundError("Required files not found")
            
            print("Loading prompts and transcript...")
            
            # Load transcript
            transcript = self.transcript_service.load_transcript()
            
            print("Fetching Linear context from SFAI workspace...")
            
            # Fetch Linear context
            linear_context = self.linear_service.get_workspace_context()
            linear_context_str = linear_context.format_for_prompt()
            
            print("Formatting prompts...")
            
            # Format prompts
            system_prompt, user_prompt = self.transcript_service.format_prompts(
                transcript, linear_context_str
            )
            
            print(f"Calling OpenAI API with model: {Config.OPENAI_MODEL}")
            
            # Process with OpenAI
            generated_issues = self.openai_service.process_transcript(
                system_prompt, user_prompt
            )
            
            processing_time = time.time() - start_time
            
            # Create result
            result = ProcessingResult(
                generated_issues=generated_issues,
                linear_context=linear_context,
                raw_ai_response="",  # Could store this if needed
                processing_time=processing_time
            )
            
            # Save results
            output_file = output_file or Config.OUTPUT_FILE
            self._save_results(result, output_file)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                generated_issues=[],
                linear_context=LinearContext(),
                raw_ai_response="",
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    def create_linear_issues(self, issues: List[GeneratedIssue]) -> List[Dict[str, Any]]:
        """Create Linear issues from generated data."""
        if not issues:
            print("No issues to create")
            return []
        
        created_issues = []
        
        print(f"\nCreating {len(issues)} issues in Jonathan Test Space...")
        
        for i, issue in enumerate(issues, 1):
            # Hardcode assignee to jonny34923@gmail.com for test workspace
            issue.assign_team_member = "jonny34923@gmail.com"
            
            print(f"\n--- Creating Issue {i}/{len(issues)} ---")
            print(f"Title: {issue.issue_title}")
            print(f"Project: {issue.project or 'No project'}")
            print(f"Assignee: {issue.assign_team_member} (hardcoded for test)")
            print(f"Priority: {issue.priority}")
            print(f"Estimate: {issue.time_estimate or 'No estimate'} points")
            print(f"Due Date: {issue.deadline or 'No deadline'}")
            
            # Convert to dict for Linear service
            issue_data = issue.to_dict()
            
            created_issue = self.test_linear_service.create_issue(issue_data)
            
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
    
    def _save_results(self, result: ProcessingResult, output_file: Path) -> None:
        """Save processing results to file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Warning: Could not save results to {output_file}: {e}")
    
    def run_full_workflow(self) -> Dict[str, Any]:
        """Run the complete workflow and return summary."""
        print("="*50)
        print("ALPHA MACHINE - TRANSCRIPT PROCESSING")
        print("="*50)
        
        # Process transcript
        result = self.process_transcript()
        
        if not result.success:
            print(f"❌ Processing failed: {result.error_message}")
            return {"success": False, "error": result.error_message}
        
        print("\n" + "="*50)
        print("GENERATED TICKETS")
        print("="*50)
        
        # Pretty print the generated issues
        for i, issue in enumerate(result.generated_issues, 1):
            print(f"\n{i}. {issue.issue_title}")
            print(f"   Description: {issue.issue_description[:100]}...")
            print(f"   Project: {issue.project or 'No project'}")
            print(f"   Priority: {issue.priority}")
            print(f"   Estimate: {issue.time_estimate or 'No estimate'} points")
        
        # Create Linear issues
        if result.generated_issues:
            print(f"\n" + "="*50)
            print("CREATING ISSUES IN LINEAR")
            print("="*50)
            
            created_issues = self.create_linear_issues(result.generated_issues)
            
            print(f"\n" + "="*50)
            print("SUMMARY")
            print("="*50)
            print(f"AI Generated: {len(result.generated_issues)} issues")
            print(f"Successfully Created: {len(created_issues)} issues")
            print(f"Failed: {len(result.generated_issues) - len(created_issues)} issues")
            print(f"Processing Time: {result.processing_time:.2f} seconds")
            
            if created_issues:
                print(f"\nCreated issues in Jonathan Test Space:")
                for issue in created_issues:
                    print(f"  - {issue['title']} (ID: {issue['id']})")
            
            return {
                "success": True,
                "generated_count": len(result.generated_issues),
                "created_count": len(created_issues),
                "processing_time": result.processing_time,
                "created_issues": created_issues
            }
        else:
            print("No issues were generated")
            return {
                "success": True,
                "generated_count": 0,
                "created_count": 0,
                "processing_time": result.processing_time,
                "created_issues": []
            } 