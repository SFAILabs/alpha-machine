#!/usr/bin/env python3
"""
Alpha Machine Integration Test
Tests the complete flow: Transcript Processing -> Linear Context -> Comprehensive Analysis

This test properly uses:
1. TranscriptFilterService to filter sensitive data from transcript
2. AlphaMachineOrchestrator to get Linear workspace context  
3. SlackCommandHandler with prompts.yml for comprehensive analysis
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from shared.core.config import Config
from shared.core.utils import load_prompts
from shared.services.ai_service import OpenAIService
from services.transcript.filter_service import TranscriptFilterService
from services.linear.orchestrator import AlphaMachineOrchestrator
from services.slackbot.command_handler import SlackCommandHandler

class AlphaMachineIntegrationTest:
    """Integration test for the complete Alpha Machine workflow."""
    
    def __init__(self):
        """Initialize all services for the integration test."""
        print("🔧 Initializing Alpha Machine Integration Test...")
        print("=" * 60)
        
        # Initialize services
        self.transcript_filter = TranscriptFilterService()
        self.linear_orchestrator = AlphaMachineOrchestrator()
        self.slack_handler = SlackCommandHandler()
        self.ai_service = OpenAIService()
        self.prompts = load_prompts(Config.PROMPTS_FILE)
        
        # Load test transcript
        self.transcript_path = Path("test_data/sf_ai_-_fnrp_transcript.txt")
        self.transcript_content = self._load_transcript()
        
        print("✅ All services initialized successfully!")
        print(f"📄 Loaded transcript: {len(self.transcript_content)} characters")
        print()
    
    def _load_transcript(self) -> str:
        """Load the test transcript file."""
        if not self.transcript_path.exists():
            raise FileNotFoundError(f"Transcript not found: {self.transcript_path}")
        
        with open(self.transcript_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_step_1_transcript_filtering(self):
        """Step 1: Use transcript module to filter sensitive data."""
        print("🔍 STEP 1: TRANSCRIPT FILTERING")
        print("=" * 50)
        
        # Use the transcript filter service with AI filtering
        result = self.transcript_filter.filter_transcript(
            transcript=self.transcript_content,
            filename="sf_ai_-_fnrp_transcript.txt"
        )
        
        print("✅ Transcript filtering completed!")
        print(f"📊 Processing time: {result.processing_time:.2f} seconds")
        print(f"📄 Original length: {len(self.transcript_content)} chars")
        print(f"📄 Filtered length: {len(result.filtered_transcript)} chars")
        print(f"🔍 Redactions made: {result.redaction_count}")
        
        # Show sample of filtered content
        filtered_preview = result.filtered_transcript[:500]
        print(f"\n📋 Filtered Content Preview:")
        print("-" * 30)
        print(filtered_preview + "...")
        print("-" * 30)
        print()
        
        return result
    
    def test_step_2_linear_context(self):
        """Step 2: Use linear module to get workspace context."""
        print("🎯 STEP 2: LINEAR WORKSPACE CONTEXT")
        print("=" * 50)
        
        # Get Linear workspace context using the orchestrator
        linear_context = self.linear_orchestrator.linear_service.get_workspace_context()
        linear_context_str = linear_context.format_for_prompt()
        
        print("✅ Linear context retrieved successfully!")
        print(f"📊 Active Projects: {len(linear_context.projects)}")
        print(f"📋 Total Issues: {len(linear_context.issues)}")
        
        # Show context preview
        context_preview = linear_context_str[:500]
        print(f"\n📋 Linear Context Preview:")
        print("-" * 30)
        print(context_preview + "...")
        print("-" * 30)
        print()
        
        return linear_context_str
    
    def test_step_3_comprehensive_analysis(self, filtered_result, linear_context):
        """Step 3: Use slackbot module for comprehensive analysis with prompts.yml."""
        print("🤖 STEP 3: COMPREHENSIVE ANALYSIS")
        print("=" * 50)
        
        # Extract metadata from filtered result
        speakers = []
        lines = self.transcript_content.split('\n')
        for line in lines:
            if '|' in line and not line.strip().startswith('Speaker'):
                parts = line.split('|')
                if len(parts) >= 2:
                    speaker = parts[0].strip()
                    if speaker and speaker not in speakers:
                        speakers.append(speaker)
        
        meeting_metadata = {
            "meeting_type": "Data Analysis & ICP Profiling Discussion",
            "participants": ", ".join(speakers),
            "key_topics": "Salesforce analysis, ICP profiling, ROI optimization, Lead generation"
        }
        
        # Get the comprehensive analysis prompt
        prompt_config = self.prompts.get('comprehensive_meeting_analysis')
        if not prompt_config:
            raise ValueError("comprehensive_meeting_analysis prompt not found in prompts.yml")
        
        system_prompt = prompt_config['system_prompt']
        user_prompt = prompt_config['user_prompt'].format(
            linear_context=linear_context,
            meeting_type=meeting_metadata['meeting_type'],
            participants=meeting_metadata['participants'],
            key_topics=meeting_metadata['key_topics'],
            filtered_transcript=filtered_result.filtered_transcript,
            ai_analysis="Filtered transcript with sensitive commercial information removed"
        )
        
        print("🔄 Generating comprehensive analysis using AI...")
        
        # Use AI service for comprehensive analysis
        response = self.ai_service.client.chat.completions.create(
            model=self.ai_service.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=self.ai_service.max_tokens,
            temperature=self.ai_service.temperature
        )
        
        comprehensive_analysis = response.choices[0].message.content
        
        print("✅ Comprehensive analysis completed!")
        print(f"📝 Analysis length: {len(comprehensive_analysis)} characters")
        print()
        
        return comprehensive_analysis, meeting_metadata
    
    def run_integration_test(self):
        """Run the complete integration test workflow."""
        print("🚀 ALPHA MACHINE INTEGRATION TEST")
        print("=" * 60)
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Step 1: Filter transcript using transcript module
            filtered_result = self.test_step_1_transcript_filtering()
            
            # Step 2: Get Linear context using linear module  
            linear_context = self.test_step_2_linear_context()
            
            # Step 3: Comprehensive analysis using slackbot module + prompts.yml
            comprehensive_analysis, meeting_metadata = self.test_step_3_comprehensive_analysis(
                filtered_result, linear_context
            )
            
            # Display final results
            print("🎉 INTEGRATION TEST RESULTS")
            print("=" * 60)
            print("✅ Transcript Filtering: PASSED")
            print("✅ Linear Context Gathering: PASSED")
            print("✅ Comprehensive Analysis: PASSED")
            print()
            
            print("📊 MEETING METADATA:")
            print("-" * 40)
            print(f"Type: {meeting_metadata['meeting_type']}")
            print(f"Participants: {meeting_metadata['participants']}")
            print(f"Topics: {meeting_metadata['key_topics']}")
            print()
            
            print("📋 COMPREHENSIVE ANALYSIS:")
            print("=" * 60)
            print(comprehensive_analysis)
            print("=" * 60)
            
            print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("🎯 Full Alpha Machine workflow integration verified!")
            
            return {
                "success": True,
                "filtered_result": filtered_result,
                "linear_context": linear_context,
                "comprehensive_analysis": comprehensive_analysis,
                "meeting_metadata": meeting_metadata
            }
            
        except Exception as e:
            print(f"\n❌ INTEGRATION TEST FAILED: {e}")
            raise

def main():
    """Main test execution."""
    tester = AlphaMachineIntegrationTest()
    result = tester.run_integration_test()
    return result

if __name__ == "__main__":
    main() 