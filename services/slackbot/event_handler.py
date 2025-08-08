"""
Slack Event Handler for Alpha Machine Bot

Handles Slack events like mentions, messages, reactions, etc.
"""

from typing import Dict, Any
import json
from datetime import datetime
import traceback

from shared.core.config import Config
from shared.services.slack_service import SlackService
from shared.services.ai_service import OpenAIService
from command_handler import SlackCommandHandler, USER_PENDING_TICKETS


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
        
        print(f"=== HANDLE_INTERACTION CALLED ===")
        print(f"Interaction type: {interaction_type}")
        print(f"Full payload: {payload}")
        
        try:
            if interaction_type == "block_actions":
                print("Calling _handle_block_actions")
                await self._handle_block_actions(payload)
            elif interaction_type == "view_submission":
                print("Calling _handle_view_submission")
                await self._handle_view_submission(payload)
            else:
                print(f"Unhandled interaction type: {interaction_type}")
                
        except Exception as e:
            print(f"Error handling interaction {interaction_type}: {e}")
            print(f"Exception details: {traceback.format_exc()}")
    
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
        
        print(f"Block actions payload: {payload}")
        
        for action in actions:
            action_id = action.get("action_id", "")
            value = action.get("value", "")
            
            print(f"Processing action_id: '{action_id}' with value: '{value}'")
            
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
            
            elif action_id == "transcript_selection":
                # Handle transcript dropdown selection - store the selection
                try:
                    selected_values = action.get("selected_options", [])
                    transcript_ids = [opt.get("value") for opt in selected_values]
                    user_id = user.get("id")
                    
                    # Store selection for this user
                    self.command_handler._store_user_selection(user_id, transcript_ids)
                    
                    selected_count = len(transcript_ids)
                    response_text = f"📋 Selected {selected_count} transcript(s). Click '✅ Use Selected' to confirm, then use `/chat [your question]`."
                    
                    # Send ephemeral response
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user_id
                    )
                    
                except Exception as e:
                    print(f"Error handling transcript selection: {e}")
            
            elif action_id == "use_selected_transcripts":
                # Handle "Use Selected" button click
                try:
                    user_id = user.get("id")
                    selected_transcript_ids = self.command_handler._get_user_selection(user_id)
                    
                    if selected_transcript_ids:
                        response_text = (
                            f"🎯 **{len(selected_transcript_ids)} transcript(s) selected!** \n\n"
                            "✅ **Ready!** Now use `/chat [your question]` and I'll analyze only the selected transcripts.\n\n"
                            "💡 **Example**: `/chat What budget decisions were made in the selected meetings?`\n\n"
                            "⏰ Selection expires in 10 minutes."
                        )
                    else:
                        response_text = (
                            "❌ **No transcripts selected.** Please select transcripts from the dropdown first, then click this button."
                        )
                    
                    # Send follow-up instructions
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user_id
                    )
                    
                except Exception as e:
                    print(f"Error handling use selected transcripts: {e}")
            
            elif action_id == "use_all_transcripts":
                # Handle "Use All Recent" button click
                try:
                    response_text = (
                        "🔄 **Using all recent transcripts!** This is the default behavior.\n"
                        "Use `/chat [your question]` normally to get context from all recent meetings.\n\n"
                        "💡 **Example**: `/chat What are our current project priorities?`"
                    )
                    
                    # Send follow-up instructions
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user.get("id")
                    )
                    
                except Exception as e:
                    print(f"Error handling use all transcripts: {e}")
            
            elif action_id == "chat_with_transcript_selection":
                # Handle transcript selection for /chat-with command
                try:
                    selected_values = action.get("selected_options", [])
                    transcript_ids = [opt.get("value") for opt in selected_values]
                    user_id = user.get("id")
                    
                    # Store selection for this user
                    self.command_handler._store_user_selection(user_id, transcript_ids)
                    
                    selected_count = len(transcript_ids)
                    response_text = f"📋 Selected {selected_count} transcript(s). Click '🚀 Answer with Selected' to get your AI response."
                    
                    # Send ephemeral response
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user_id
                    )
                    
                except Exception as e:
                    print(f"Error handling chat-with transcript selection: {e}")
            
            elif action_id == "answer_with_selected":
                # Handle "Answer with Selected" button - process immediately
                try:
                    user_id = user.get("id")
                    user_question = value  # The question is stored in the button value
                    selected_transcript_ids = self.command_handler._get_user_selection(user_id)
                    
                    if selected_transcript_ids and user_question:
                        # Clear the selection and process the query
                        self.command_handler._clear_user_selection(user_id)
                        
                        # Process the chat with selected transcripts
                        response = await self.command_handler._handle_chat_with_selected_transcripts(
                            selected_transcript_ids, user_question
                        )
                        
                        # Send the AI response
                        response_text = response.get('text', 'No response generated')
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=response_text,
                            user=user_id
                        )
                    else:
                        error_msg = "❌ Please select transcripts first, or the question was not found."
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=error_msg,
                            user=user_id
                        )
                        
                except Exception as e:
                    print(f"Error handling answer with selected: {e}")
                    error_msg = f"❌ Error processing your request: {str(e)}"
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=error_msg,
                        user=user.get("id")
                    )
            
            elif action_id == "answer_with_all":
                # Handle "Use All Recent" button - process with default context
                try:
                    user_id = user.get("id")
                    user_question = value  # The question is stored in the button value
                    
                    if user_question:
                        # Create a mock payload for the regular chat command
                        chat_payload = {
                            "text": user_question,
                            "channel_id": channel.get("id"),
                            "user_id": user_id
                        }
                        
                        # Process with regular chat command (uses all recent transcripts)
                        response = await self.command_handler._handle_chat_command(chat_payload)
                        
                        # Send the AI response
                        response_text = response.get('text', 'No response generated')
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=response_text,
                            user=user_id
                        )
                    else:
                        error_msg = "❌ Question not found."
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=error_msg,
                            user=user_id
                        )
                        
                except Exception as e:
                    print(f"Error handling answer with all: {e}")
                    error_msg = f"❌ Error processing your request: {str(e)}"
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=error_msg,
                        user=user.get("id")
                    )
            
            elif action_id == "chat_inline_transcript_selection":
                # Handle transcript selection for /chat with [question]
                try:
                    selected_values = action.get("selected_options", [])
                    transcript_ids = [opt.get("value") for opt in selected_values]
                    user_id = user.get("id")
                    
                    # Store selection for this user
                    self.command_handler._store_user_selection(user_id, transcript_ids)
                    
                    selected_count = len(transcript_ids)
                    response_text = f"📋 Selected {selected_count} transcript(s). Click '🚀 Answer with Selected' to get your AI response."
                    
                    # Send ephemeral response
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user_id
                    )
                    
                except Exception as e:
                    print(f"Error handling chat inline transcript selection: {e}")
            
            elif action_id == "answer_inline_selected":
                # Handle "Answer with Selected" button for inline questions
                try:
                    user_id = user.get("id")
                    user_question = value  # The question is stored in the button value
                    selected_transcript_ids = self.command_handler._get_user_selection(user_id)
                    
                    if selected_transcript_ids and user_question:
                        # Clear the selection and process the query
                        self.command_handler._clear_user_selection(user_id)
                        
                        # Process the chat with selected transcripts
                        response = await self.command_handler._handle_chat_with_selected_transcripts(
                            selected_transcript_ids, user_question
                        )
                        
                        # Send the AI response
                        response_text = response.get('text', 'No response generated')
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=response_text,
                            user=user_id
                        )
                    else:
                        error_msg = "❌ Please select transcripts first, or the question was not found."
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=error_msg,
                            user=user_id
                        )
                        
                except Exception as e:
                    print(f"Error handling answer inline selected: {e}")
                    error_msg = f"❌ Error processing your request: {str(e)}"
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=error_msg,
                        user=user.get("id")
                    )
            
            elif action_id == "answer_inline_all":
                # Handle "Use All Recent" button for inline questions
                try:
                    user_id = user.get("id")
                    user_question = value  # The question is stored in the button value
                    
                    if user_question:
                        # Create a mock payload for the regular chat command
                        chat_payload = {
                            "text": user_question,
                            "channel_id": channel.get("id"),
                            "user_id": user_id
                        }
                        
                        # Process with regular chat command (uses all recent transcripts)
                        response = await self.command_handler._handle_chat_command(chat_payload)
                        
                        # Send the AI response
                        response_text = response.get('text', 'No response generated')
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=response_text,
                            user=user_id
                        )
                    else:
                        error_msg = "❌ Question not found."
                        self.slack_service.send_message(
                            channel=channel.get("id"),
                            text=error_msg,
                            user=user_id
                        )
                        
                except Exception as e:
                    print(f"Error handling answer inline all: {e}")
                    error_msg = f"❌ Error processing your request: {str(e)}"
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=error_msg,
                        user=user.get("id")
                    )
            
            elif action_id == "chat_select_transcript_selection":
                # Handle transcript selection for /chat select
                try:
                    selected_values = action.get("selected_options", [])
                    transcript_ids = [opt.get("value") for opt in selected_values]
                    user_id = user.get("id")
                    
                    # Store selection for this user
                    self.command_handler._store_user_selection(user_id, transcript_ids)
                    
                    selected_count = len(transcript_ids)
                    response_text = f"📋 Selected {selected_count} transcript(s). Click '✅ Set Selection' to confirm."
                    
                    # Send ephemeral response
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user_id
                    )
                    
                except Exception as e:
                    print(f"Error handling chat select transcript selection: {e}")
            
            elif action_id == "set_transcript_selection":
                # Handle "Set Selection" button for /chat select
                try:
                    user_id = user.get("id")
                    selected_transcript_ids = self.command_handler._get_user_selection(user_id)
                    
                    if selected_transcript_ids:
                        response_text = (
                            f"✅ **{len(selected_transcript_ids)} transcript(s) selected!** \n\n"
                            "🎯 **Ready!** Now use `/chat [your question]` and I'll analyze only the selected transcripts.\n\n"
                            "💡 **Example**: `/chat What budget decisions were made?`\n\n"
                            "⏰ Selection expires in 10 minutes."
                        )
                    else:
                        response_text = (
                            "❌ **No transcripts selected.** Please select transcripts from the dropdown first, then click this button."
                        )
                    
                    self.slack_service.send_message(
                        channel=channel.get("id"),
                        text=response_text,
                        user=user_id
                    )
                    
                except Exception as e:
                    print(f"Error handling set transcript selection: {e}")
            
            elif action_id == "create_tickets_yes":
                # Handle "Yes, Create Tickets" button
                try:
                    # Debug: Print what we're getting
                    print(f"YES button payload - action: {action}")
                    print(f"YES button payload - user: {user}")
                    print(f"YES button payload - value: {value}")
                    
                    # Get user ID and any compact payload from value
                    user_id = user.get("id")
                    try:
                        value_payload = json.loads(value) if value else {}
                        # Fallback to user-provided compact payload
                        if value_payload and value_payload.get("analysis") and value_payload.get("original_request"):
                            # Seed the pending cache in case a different instance handles the interaction
                            self.command_handler._clear_pending_tickets(user_id)
                            USER_PENDING_TICKETS[user_id] = {
                                "context": "",  # context not needed for conversion
                                "original_request": value_payload.get("original_request"),
                                "analysis": value_payload.get("analysis"),
                                "timestamp": datetime.now(),
                                "user_id": user_id
                            }
                    except Exception:
                        pass
                    
                    print(f"Processing YES button click for user: {user_id}")
                    
                    # Immediately acknowledge with a loading message (do not replace the preview message)
                    response_url = payload.get("response_url")
                    if response_url:
                        self.slack_service.respond_to_interaction(response_url, {
                            "response_type": "ephemeral",
                            "replace_original": False,
                            "text": "⏳ Creating tickets..."
                        })

                    # Process the ticket creation
                    response = await self.command_handler.handle_create_tickets_confirmation(user_id, True)
                    
                    print(f"Got response: {response}")
                    
                    # Final response: send another ephemeral (do NOT replace the preview message)
                    response_text = response.get('text', 'No response generated')
                    if response_url:
                        self.slack_service.respond_to_interaction(response_url, {
                            "response_type": "ephemeral",
                            "replace_original": False,
                            "text": response_text
                        })
                    else:
                        # Fallback if no response_url
                        self.slack_service.send_ephemeral_message(
                            channel=channel.get("id"),
                            user=user.get("id"),
                            text=response_text
                        )
                    
                except Exception as e:
                    print(f"Error handling create tickets yes: {e}")
                    print(f"Exception details: {traceback.format_exc()}")
                    error_msg = f"❌ Error creating tickets: {str(e)}"
                    if response_url:
                        self.slack_service.respond_to_interaction(response_url, {
                            "response_type": "ephemeral",
                            "replace_original": True,
                            "text": error_msg
                        })
                    else:
                        self.slack_service.send_ephemeral_message(
                            channel=channel.get("id"),
                            user=user.get("id"),
                            text=error_msg
                        )
            
            elif action_id == "create_tickets_no":
                # Handle "No, Cancel" button
                try:
                    # Debug: Print what we're getting
                    print(f"NO button payload - action: {action}")
                    print(f"NO button payload - user: {user}")
                    print(f"NO button payload - value: {value}")
                    
                    # Get user ID from payload (standard way)
                    user_id = user.get("id")
                    
                    print(f"Processing NO button click for user: {user_id}")
                    
                    # Immediately acknowledge cancellation (do not replace the preview message)
                    response_url = payload.get("response_url")
                    if response_url:
                        self.slack_service.respond_to_interaction(response_url, {
                            "response_type": "ephemeral",
                            "replace_original": False,
                            "text": "🚫 Cancelling..."
                        })

                    # Process the cancellation
                    response = await self.command_handler.handle_create_tickets_confirmation(user_id, False)
                    
                    print(f"Got response: {response}")
                    
                    # Final response: send another ephemeral (do NOT replace the preview message)
                    response_text = response.get('text', 'No response generated')
                    if response_url:
                        self.slack_service.respond_to_interaction(response_url, {
                            "response_type": "ephemeral",
                            "replace_original": False,
                            "text": response_text
                        })
                    else:
                        self.slack_service.send_ephemeral_message(
                            channel=channel.get("id"),
                            user=user.get("id"),
                            text=response_text
                        )
                    
                except Exception as e:
                    print(f"Error handling create tickets no: {e}")
                    print(f"Exception details: {traceback.format_exc()}")
                    error_msg = f"❌ Error processing cancellation: {str(e)}"
                    if response_url:
                        self.slack_service.respond_to_interaction(response_url, {
                            "response_type": "ephemeral",
                            "replace_original": True,
                            "text": error_msg
                        })
                    else:
                        self.slack_service.send_ephemeral_message(
                            channel=channel.get("id"),
                            user=user.get("id"),
                            text=error_msg
                        )
            
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