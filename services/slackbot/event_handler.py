"""
Slack Event Handler for Alpha Machine Bot

Handles Slack events like mentions, messages, reactions, etc.
"""

from typing import Dict, Any
from datetime import datetime

from shared.core.config import Config
from shared.services.slack_service import SlackService
from shared.services.ai_service import OpenAIService
from command_handler import SlackCommandHandler


class SlackEventHandler:
    """Handles processing of Slack events."""
    
    def __init__(self):
        """Initialize services."""
        self.slack_service = SlackService()
        self.ai_service = OpenAIService(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        self.command_handler = SlackCommandHandler()
    
    async def handle_event(self, payload: Dict[str, Any]) -> None:
        """Route event to appropriate handler."""
        event = payload.get("event", {})
        event_type = event.get("type", "")
        
        try:
            if event_type == "app_mention":
                await self._handle_app_mention(event)
            elif event_type == "message":
                await self._handle_message(event)
            elif event_type == "reaction_added":
                await self._handle_reaction_added(event)
            elif event_type == "team_join":
                await self._handle_team_join(event)
            else:
                print(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            print(f"Error handling event {event_type}: {e}")
    
    async def handle_interaction(self, payload: Dict[str, Any]) -> None:
        """Handle interactive components (buttons, modals, etc.)."""
        interaction_type = payload.get("type", "")
        
        try:
            if interaction_type == "block_actions":
                await self._handle_block_actions(payload)
            elif interaction_type == "view_submission":
                await self._handle_view_submission(payload)
            else:
                print(f"Unhandled interaction type: {interaction_type}")
                
        except Exception as e:
            print(f"Error handling interaction {interaction_type}: {e}")
    
    async def _handle_app_mention(self, event: Dict[str, Any]) -> None:
        """Handle when the bot is mentioned."""
        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        
        # Remove the bot mention from the text
        bot_user_id = Config.SLACK_BOT_USER_ID or "bot"
        text = text.replace(f"<@{bot_user_id}>", "").strip()
        
        if not text:
            text = "Hello! How can I help you?"
        
        try:
            # Get comprehensive context and generate response
            context = await self.command_handler._get_comprehensive_context()
            
            system_prompt = """You are Alpha Machine, an AI assistant for a consulting firm. 
Someone just mentioned you in Slack. Respond helpfully and conversationally.
You have access to meeting transcripts, Linear projects, and team information.
Keep responses concise but helpful. Use emojis appropriately."""

            user_prompt = f"""Context: {context}

User mentioned me and said: {text}

Please respond helpfully."""

            ai_response = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            response_text = ai_response if ai_response else "Hi there! I'm here to help with your questions."
            
            # Send response to the channel
            self.slack_service.send_message(
                channel=channel_id,
                text=f"👋 {response_text}"
            )
            
        except Exception as e:
            # Send error message
            self.slack_service.send_message(
                channel=channel_id,
                text=f"❌ Sorry, I encountered an error: {str(e)}"
            )
    
    async def _handle_message(self, event: Dict[str, Any]) -> None:
        """Handle direct messages to the bot."""
        # Only handle direct messages (DMs)
        channel_type = event.get("channel_type")
        if channel_type != "im":
            return
        
        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        
        # Ignore bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return
        
        if not text.strip():
            return
        
        try:
            # Get context and generate response
            context = await self.command_handler._get_comprehensive_context()
            
            system_prompt = """You are Alpha Machine, an AI assistant for a consulting firm.
Someone sent you a direct message. Respond helpfully and conversationally.
You have access to meeting transcripts, Linear projects, and team information.
Keep responses concise but helpful."""

            user_prompt = f"""Context: {context}

User sent me a DM: {text}

Please respond helpfully."""

            ai_response = await self.ai_service.generate_text_async(system_prompt, user_prompt)
            response_text = ai_response if ai_response else "Hi! I'm here to help. You can ask me about projects, meetings, or use slash commands like /chat."
            
            # Send response to the DM
            self.slack_service.send_message(
                channel=channel_id,
                text=response_text
            )
            
        except Exception as e:
            # Send error message
            self.slack_service.send_message(
                channel=channel_id,
                text=f"❌ Sorry, I encountered an error: {str(e)}"
            )
    
    async def _handle_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle when someone adds a reaction."""
        reaction = event.get("reaction")
        user_id = event.get("user")
        item = event.get("item", {})
        
        # Example: If someone reacts with 📝 to a message, offer to summarize
        if reaction == "memo" or reaction == "pencil":
            channel_id = item.get("channel")
            if channel_id:
                try:
                    self.slack_service.send_ephemeral_message(
                        channel=channel_id,
                        user=user_id,
                        text="📝 I noticed you added a memo reaction! Use `/summarize` to get AI summaries of meetings or client status."
                    )
                except Exception as e:
                    print(f"Error sending reaction response: {e}")
    
    async def _handle_team_join(self, event: Dict[str, Any]) -> None:
        """Handle when someone joins the team."""
        user = event.get("user", {})
        user_name = user.get("real_name") or user.get("name", "New team member")
        user_id = user.get("id")
        
        try:
            # Send welcome message via DM
            welcome_message = f"""🎉 Welcome to the team, {user_name}!

I'm Alpha Machine, your AI assistant. I can help you with:

🤖 `/chat` - Ask me anything about projects, meetings, or the team
📊 `/summarize` - Get meeting summaries or client status updates  
🎯 `/create` - Analyze and create Linear tickets
👤 `/teammember` - Get info about team members and their work
📈 `/weekly-summary` - Generate comprehensive weekly reports

Feel free to mention me (@Alpha Machine) in any channel or send me a DM anytime!"""

            # Get user's DM channel
            dm_channel = self.slack_service.open_dm(user_id)
            if dm_channel:
                self.slack_service.send_message(
                    channel=dm_channel,
                    text=welcome_message
                )
                
        except Exception as e:
            print(f"Error sending welcome message: {e}")
    
    async def _handle_block_actions(self, payload: Dict[str, Any]) -> None:
        """Handle button clicks and other block actions."""
        actions = payload.get("actions", [])
        user = payload.get("user", {})
        channel = payload.get("channel", {})
        
        for action in actions:
            action_id = action.get("action_id", "")
            value = action.get("value", "")
            
            if action_id == "generate_summary":
                # Handle summary generation button
                try:
                    # Get context and generate summary
                    context = await self.command_handler._get_comprehensive_context()
                    
                    summary_response = {
                        "response_type": "ephemeral",
                        "text": f"📊 **Quick Summary Generated:**\n\n{context[:500]}..."
                    }
                    
                    # Update the original message
                    self.slack_service.update_message(
                        channel=channel.get("id"),
                        ts=payload.get("message", {}).get("ts"),
                        text="Summary generated! ✅"
                    )
                    
                except Exception as e:
                    print(f"Error handling summary button: {e}")
            
            # Add more button handlers as needed
    
    async def _handle_view_submission(self, payload: Dict[str, Any]) -> None:
        """Handle modal form submissions."""
        view = payload.get("view", {})
        callback_id = view.get("callback_id", "")
        
        if callback_id == "feedback_modal":
            # Handle feedback form submission
            values = view.get("state", {}).get("values", {})
            # Process feedback values
            print(f"Received feedback: {values}")
        
        # Add more modal handlers as needed 