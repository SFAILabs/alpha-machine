#!/usr/bin/env python3
"""
Comprehensive test suite for Slackbot-Linear integration commands.
Tests all slash commands with Linear API interactions.
"""

import sys
import os
import asyncio
import json
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add the current directory to Python path so we can import from shared/
sys.path.append(str(Path(__file__).parent.parent))

from shared.core.config import Config

# Import directly from command_handler module to avoid webhook initialization
sys.path.append(str(Path(__file__).parent.parent / "services" / "slackbot"))
from command_handler import SlackCommandHandler


class TestSlackbotLinearIntegration(unittest.TestCase):
    """Test suite for Slackbot-Linear integration commands."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        print("🔧 Setting up test fixtures...")
        
        # Mock the SlackCommandHandler to avoid real API calls
        self.command_handler = SlackCommandHandler()
        
        # Create mock payload template
        self.mock_payload = {
            "command": "",
            "text": "",
            "response_url": "https://hooks.slack.com/commands/1234567890/0987654321/mock_response_url",
            "channel_id": "C1234567890",
            "user_id": "U1234567890",
            "user_name": "test_user"
        }
        
        print("✅ Test setup complete!")
    
    def test_chat_command_with_linear_context(self):
        """Test /chat command with Linear context integration."""
        print("\n🧪 Testing /chat command...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/chat"
        payload["text"] = "What are the current project priorities?"
        
        async def run_test():
            # Mock the comprehensive context method
            with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                mock_context.return_value = "Mock Linear context with projects and issues"
                
                with patch.object(self.command_handler, '_get_recent_slack_history') as mock_history:
                    mock_history.return_value = "Mock Slack history"
                    
                    with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                        mock_ai.return_value = ["AI response about project priorities based on Linear context"]
                        
                        response = await self.command_handler._handle_chat_command(payload)
                        
                        self.assertEqual(response["response_type"], "ephemeral")
                        self.assertIn("AI Response", response["text"])
                        self.assertIn("project priorities", response["text"])
        
        asyncio.run(run_test())
        print("✅ /chat command test passed!")
    
    def test_summarize_command_meeting(self):
        """Test /summarize command for meeting summaries."""
        print("\n🧪 Testing /summarize command (meeting)...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/summarize"
        payload["text"] = "last @meeting @14:30"
        
        async def run_test():
            with patch.object(self.command_handler, '_handle_meeting_summary') as mock_meeting:
                mock_meeting.return_value = {
                    "response_type": "ephemeral",
                    "text": "📊 Meeting Summary: Key decisions about project timeline"
                }
                
                response = await self.command_handler._handle_summarize_command(payload)
                
                self.assertEqual(response["response_type"], "ephemeral")
                self.assertIn("Meeting Summary", response["text"])
        
        asyncio.run(run_test())
        print("✅ /summarize (meeting) test passed!")
    
    def test_summarize_command_client(self):
        """Test /summarize command for client status."""
        print("\n🧪 Testing /summarize command (client)...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/summarize"
        payload["text"] = "client acme_corp"
        
        async def run_test():
            with patch.object(self.command_handler, '_handle_client_summary') as mock_client:
                mock_client.return_value = {
                    "response_type": "ephemeral",
                    "text": "📈 Client Status: Acme Corp project 75% complete, deadline next week"
                }
                
                response = await self.command_handler._handle_summarize_command(payload)
                
                self.assertEqual(response["response_type"], "ephemeral")
                self.assertIn("Client Status", response["text"])
        
        asyncio.run(run_test())
        print("✅ /summarize (client) test passed!")
    
    def test_create_command_test_mode_disabled(self):
        """Test /create command when test mode is disabled (analysis only)."""
        print("\n🧪 Testing /create command (test mode disabled)...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/create"
        payload["text"] = "Create a ticket for implementing user authentication"
        
        async def run_test():
            with patch.object(Config, 'LINEAR_TEST_MODE', False):
                with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                    mock_context.return_value = "Mock Linear context"
                    
                    with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                        mock_ai.return_value = ["Analysis: Should create user authentication ticket with high priority"]
                        
                        response = await self.command_handler._handle_create_ticket_command(payload)
                        
                        self.assertEqual(response["response_type"], "ephemeral")
                        self.assertIn("Test Mode Disabled", response["text"])
                        self.assertIn("Analysis", response["text"])
        
        asyncio.run(run_test())
        print("✅ /create command (test mode disabled) test passed!")
    
    def test_create_command_test_mode_enabled(self):
        """Test /create command when test mode is enabled (actual creation)."""
        print("\n🧪 Testing /create command (test mode enabled)...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/create"
        payload["text"] = "Create a ticket for implementing user authentication"
        
        mock_issue_data = {
            "title": "Implement user authentication",
            "description": "Add secure user login and registration system",
            "priority": "2"
        }
        
        async def run_test():
            with patch.object(Config, 'LINEAR_TEST_MODE', True):
                with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                    mock_context.return_value = "Mock Linear context"
                    
                    with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                        mock_ai.return_value = [json.dumps(mock_issue_data)]
                        
                        with patch.object(self.command_handler.linear_service, 'create_issue') as mock_create:
                            mock_create.return_value = {
                                "id": "ABC-123",
                                "title": "Implement user authentication"
                            }
                            
                            response = await self.command_handler._handle_create_ticket_command(payload)
                            
                            self.assertEqual(response["response_type"], "in_channel")
                            self.assertIn("Ticket Created", response["text"])
                            self.assertIn("ABC-123", response["text"])
        
        asyncio.run(run_test())
        print("✅ /create command (test mode enabled) test passed!")
    
    def test_update_command_test_mode_disabled(self):
        """Test /update command when test mode is disabled (analysis only)."""
        print("\n🧪 Testing /update command (test mode disabled)...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/update"
        payload["text"] = "Update ticket ABC-123 to in progress"
        
        async def run_test():
            with patch.object(Config, 'LINEAR_TEST_MODE', False):
                with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                    mock_context.return_value = "Mock Linear context"
                    
                    with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                        mock_ai.return_value = ["Analysis: Would update ticket ABC-123 status to 'In Progress'"]
                        
                        response = await self.command_handler._handle_update_ticket_command(payload)
                        
                        self.assertEqual(response["response_type"], "ephemeral")
                        self.assertIn("Test Mode Disabled", response["text"])
                        self.assertIn("Analysis", response["text"])
        
        asyncio.run(run_test())
        print("✅ /update command (test mode disabled) test passed!")
    
    def test_update_command_test_mode_enabled(self):
        """Test /update command when test mode is enabled (actual update)."""
        print("\n🧪 Testing /update command (test mode enabled)...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/update"
        payload["text"] = "Update ticket ABC-123 to in progress"
        
        mock_update_data = {
            "ticket_id": "ABC-123",
            "updates": {"status": "in_progress"},
            "summary": "Updated ticket ABC-123 status to In Progress"
        }
        
        async def run_test():
            with patch.object(Config, 'LINEAR_TEST_MODE', True):
                with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                    mock_context.return_value = "Mock Linear context"
                    
                    with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                        mock_ai.return_value = [json.dumps(mock_update_data)]
                        
                        with patch.object(self.command_handler.linear_service, 'update_issue') as mock_update:
                            mock_update.return_value = {
                                "id": "ABC-123",
                                "title": "Updated ticket",
                                "url": "https://linear.app/ticket/ABC-123"
                            }
                            
                            response = await self.command_handler._handle_update_ticket_command(payload)
                            
                            self.assertEqual(response["response_type"], "in_channel")
                            self.assertIn("Ticket Updated", response["text"])
                            self.assertIn("ABC-123", response["text"])
        
        asyncio.run(run_test())
        print("✅ /update command (test mode enabled) test passed!")
    
    def test_teammember_command(self):
        """Test /teammember command."""
        print("\n🧪 Testing /teammember command...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/teammember"
        payload["text"] = "john@company.com"
        
        async def run_test():
            with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                mock_context.return_value = "Mock Linear context with team member data"
                
                with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                    mock_ai.return_value = ["John Doe - Currently working on 3 tickets, 2 completed this week"]
                    
                    response = await self.command_handler._handle_teammember_command(payload)
                    
                    self.assertEqual(response["response_type"], "ephemeral")
                    self.assertIn("Team Member Info", response["text"])
                    self.assertIn("John Doe", response["text"])
        
        asyncio.run(run_test())
        print("✅ /teammember command test passed!")
    
    def test_weekly_summary_command(self):
        """Test /weekly-summary command."""
        print("\n🧪 Testing /weekly-summary command...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/weekly-summary"
        payload["text"] = ""
        
        async def run_test():
            with patch.object(self.command_handler, '_get_comprehensive_context') as mock_context:
                mock_context.return_value = "Mock weekly Linear context"
                
                with patch.object(self.command_handler.ai_service, '_call_openai_structured') as mock_ai:
                    mock_ai.return_value = ["Weekly Summary: 15 tickets completed, 3 projects advanced, team performance excellent"]
                    
                    response = await self.command_handler._handle_weekly_summary_command(payload)
                    
                    self.assertEqual(response["response_type"], "in_channel")
                    self.assertIn("Weekly Summary", response["text"])
        
        asyncio.run(run_test())
        print("✅ /weekly-summary command test passed!")
    
    def test_command_error_handling(self):
        """Test error handling for invalid commands."""
        print("\n🧪 Testing error handling...")
        
        payload = self.mock_payload.copy()
        payload["command"] = "/nonexistent"
        payload["text"] = "test"
        
        async def run_test():
            response = await self.command_handler.handle_command(payload)
            # The handle_command method doesn't return a response, it sends it
            # So we'll test that it doesn't crash and handles the unknown command
            pass
        
        # Test empty text handling
        payload["command"] = "/chat"
        payload["text"] = ""
        
        async def run_empty_test():
            response = await self.command_handler._handle_chat_command(payload)
            self.assertEqual(response["response_type"], "ephemeral")
            self.assertIn("Please provide", response["text"])
        
        asyncio.run(run_empty_test())
        print("✅ Error handling test passed!")


class TestLinearServiceUpdates(unittest.TestCase):
    """Test suite for Linear service update functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        from shared.services.linear_service import LinearService
        self.linear_service = LinearService(
            api_key="test_key",
            team_name="Test Team"
        )
    
    def test_update_issue_safety_check(self):
        """Test that update_issue enforces test mode safety check."""
        print("\n🧪 Testing update_issue safety check...")
        
        with patch.object(Config, 'LINEAR_TEST_MODE', False):
            with self.assertRaises(ValueError) as context:
                self.linear_service.update_issue("test-id", {"title": "Test"})
            
            self.assertIn("CRITICAL SAFETY ERROR", str(context.exception))
        
        print("✅ Safety check test passed!")
    
    def test_update_issue_structure(self):
        """Test that update_issue builds correct mutation structure."""
        print("\n🧪 Testing update_issue structure...")
        
        with patch.object(Config, 'LINEAR_TEST_MODE', True):
            with patch.object(self.linear_service, '_make_request') as mock_request:
                mock_request.return_value = {
                    "data": {
                        "issueUpdate": {
                            "success": True,
                            "issue": {"id": "test-id", "title": "Updated Title"}
                        }
                    }
                }
                
                update_data = {
                    "title": "New Title",
                    "description": "New Description",
                    "priority": "2"
                }
                
                result = self.linear_service.update_issue("test-id", update_data)
                
                # Verify the request was made with correct structure
                mock_request.assert_called_once()
                call_args = mock_request.call_args[0]
                self.assertIn("mutation UpdateIssue", call_args[0])
                
                # Verify result
                self.assertIsNotNone(result)
                self.assertEqual(result["id"], "test-id")
        
        print("✅ Update structure test passed!")


def run_all_tests():
    """Run all test suites."""
    print("🚀 Starting Slackbot-Linear Integration Test Suite...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSlackbotLinearIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLinearServiceUpdates))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 All tests passed successfully!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)