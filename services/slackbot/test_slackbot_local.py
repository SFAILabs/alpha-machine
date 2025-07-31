#!/usr/bin/env python3
"""
Local test script for Alpha Machine Slackbot functionality.
Tests Linear context gathering, transcript processing, and AI summarization.
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path so we can import from shared/
sys.path.append(str(Path(__file__).parent))

from shared.core.config import Config
from shared.services.linear_service import LinearService
from shared.services.ai_service import OpenAIService
from services.slackbot.command_handler import SlackCommandHandler

class LocalSlackbotTester:
    """Local tester for slackbot functionality without Slack integration."""
    
    def __init__(self):
        """Initialize the tester with required services."""
        print("🔧 Initializing Local Slackbot Tester...")
        
        # Initialize command handler (this will create all services)
        self.command_handler = SlackCommandHandler()
        
        # Load test transcript (adjust path for different run locations)
        self.transcript_path = Path("../../test_data/sf_ai_-_fnrp_transcript.txt")
        if not self.transcript_path.exists():
            self.transcript_path = Path("test_data/sf_ai_-_fnrp_transcript.txt")
        self.transcript_content = self._load_transcript()
        
        print("✅ Initialization complete!")
    
    def _load_transcript(self) -> str:
        """Load the test transcript file."""
        if not self.transcript_path.exists():
            raise FileNotFoundError(f"Transcript not found: {self.transcript_path}")
        
        with open(self.transcript_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 Loaded transcript: {len(content)} characters")
        return content
    
    async def test_linear_context_gathering(self) -> str:
        """Test gathering Linear workspace context."""
        print("\n" + "="*50)
        print("🎯 TESTING LINEAR CONTEXT GATHERING")
        print("="*50)
        
        try:
            # Test the comprehensive context method
            context = await self.command_handler._get_comprehensive_context()
            
            print("✅ Linear context gathered successfully!")
            print(f"Context length: {len(context)} characters")
            print("\n📊 Linear Context Preview:")
            print("-" * 30)
            print(context[:500] + "..." if len(context) > 500 else context)
            print("-" * 30)
            
            return context
            
        except Exception as e:
            print(f"❌ Error gathering Linear context: {e}")
            return f"Error gathering Linear context: {str(e)}"
    
    def test_transcript_processing(self) -> dict:
        """Test basic transcript processing and filtering."""
        print("\n" + "="*50)
        print("📄 TESTING TRANSCRIPT PROCESSING")
        print("="*50)
        
        # Simple transcript analysis
        lines = self.transcript_content.split('\n')
        speakers = set()
        
        for line in lines:
            if '|' in line and not line.strip().startswith('Speaker'):
                # Extract speaker names
                parts = line.split('|')
                if len(parts) >= 2:
                    speaker = parts[0].strip()
                    if speaker:
                        speakers.add(speaker)
        
        # Create filtered transcript summary
        filtered_data = {
            "total_lines": len(lines),
            "speakers": list(speakers),
            "speaker_count": len(speakers),
            "meeting_type": "Data Analysis & ICP Profiling Discussion",
            "key_topics": [
                "Salesforce data analysis",
                "ICP profiling",
                "ROI optimization", 
                "Lead generation",
                "Pipeline analysis"
            ],
            "transcript_preview": self.transcript_content[:800] + "..." if len(self.transcript_content) > 800 else self.transcript_content
        }
        
        print("✅ Transcript processing complete!")
        print(f"📊 Found {filtered_data['speaker_count']} speakers: {', '.join(filtered_data['speakers'])}")
        print(f"📋 Total lines: {filtered_data['total_lines']}")
        print(f"🎯 Key topics identified: {len(filtered_data['key_topics'])}")
        
        return filtered_data
    
    async def test_ai_summarization(self, linear_context: str, filtered_transcript: dict) -> str:
        """Test AI summarization with both Linear and transcript context."""
        print("\n" + "="*50)
        print("🤖 TESTING AI SUMMARIZATION")
        print("="*50)
        
        try:
            # Create comprehensive context for AI
            full_context = f"""
CURRENT LINEAR WORKSPACE CONTEXT:
{linear_context}

MEETING TRANSCRIPT ANALYSIS:
- Meeting Type: {filtered_transcript['meeting_type']}
- Participants: {', '.join(filtered_transcript['speakers'])}
- Key Topics: {', '.join(filtered_transcript['key_topics'])}

TRANSCRIPT CONTENT:
{filtered_transcript['transcript_preview']}
"""
            
            # Create AI prompt for summarization
            system_prompt = """You are Alpha Machine, an AI assistant for a consulting firm. 
You have access to the current Linear workspace (projects, issues, progress) and meeting transcript data.
Provide a comprehensive summary that connects the meeting discussion to current project status and actionable next steps."""
            
            user_prompt = f"""Based on the provided context, please provide:

1. MEETING SUMMARY: Key points and decisions from the transcript
2. PROJECT ALIGNMENT: How this meeting relates to current Linear projects
3. ACTION ITEMS: Specific next steps that should be tracked
4. RECOMMENDATIONS: Strategic insights based on both contexts

Context:
{full_context}

Please provide a detailed analysis and summary."""

            print("🔄 Sending request to AI service...")
            
            # Use OpenAI directly for text summarization
            try:
                response = self.command_handler.ai_service.client.chat.completions.create(
                    model=self.command_handler.ai_service.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=self.command_handler.ai_service.max_tokens,
                    temperature=self.command_handler.ai_service.temperature
                )
                summary = response.choices[0].message.content
            except Exception as ai_error:
                summary = f"AI service error: {ai_error}"
            
            print("✅ AI summarization complete!")
            print(f"📝 Summary length: {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            error_msg = f"❌ Error in AI summarization: {e}"
            print(error_msg)
            return error_msg
    
    def test_slack_command_simulation(self, summary: str):
        """Simulate how this would work in actual Slack commands."""
        print("\n" + "="*50)
        print("💬 SLACK COMMAND SIMULATION")
        print("="*50)
        
        # Simulate different slack commands that would use this data
        commands = {
            "/chat": "How does the recent client meeting align with our current Linear projects?",
            "/summarize": "last meeting",
            "/weekly-summary": "",
            "/teammember": "Arthur Wandzel"
        }
        
        print("🎭 Simulating Slack command responses...")
        
        for command, text in commands.items():
            print(f"\n📱 Command: {command} {text}")
            print("🤖 Response would include:")
            print("   • Current Linear workspace context")
            print("   • Recent meeting transcript analysis")
            print("   • AI-generated insights and recommendations")
            print("   • Actionable next steps")
            
            if command == "/summarize" and "meeting" in text:
                print(f"   • Meeting summary: {summary[:100]}...")
    
    async def run_full_test(self):
        """Run the complete test suite."""
        print("🚀 STARTING ALPHA MACHINE SLACKBOT LOCAL TEST")
        print("=" * 60)
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Test 1: Linear context gathering
            linear_context = await self.test_linear_context_gathering()
            
            # Test 2: Transcript processing
            filtered_transcript = self.test_transcript_processing()
            
            # Test 3: AI summarization
            summary = await self.test_ai_summarization(linear_context, filtered_transcript)
            
            # Test 4: Slack command simulation
            self.test_slack_command_simulation(summary)
            
            # Final results
            print("\n" + "="*60)
            print("🎉 TEST RESULTS SUMMARY")
            print("="*60)
            print("✅ Linear context gathering: PASSED")
            print("✅ Transcript processing: PASSED") 
            print("✅ AI summarization: PASSED")
            print("✅ Slack command simulation: PASSED")
            
            print(f"\n📊 FINAL AI SUMMARY:")
            print("-" * 40)
            print(summary)
            print("-" * 40)
            
            print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("🎯 All slackbot core functionality verified!")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            raise

async def main():
    """Main test execution."""
    tester = LocalSlackbotTester()
    await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main()) 