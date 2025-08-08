"""
Slack service for Slack operations across all flows.
"""

from typing import Dict, Any, List, Optional
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from shared.core.config import Config


class SlackService:
    """Service for Slack operations."""
    
    def __init__(self):
        """Initialize Slack client."""
        self.client: Optional[WebClient] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Slack client with configuration."""
        if Config.SLACK_BOT_TOKEN:
            self.client = WebClient(token=Config.SLACK_BOT_TOKEN)
        else:
            print("Warning: Slack bot token not configured")
    
    def send_message(self, channel: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Send message to Slack channel."""
        if not self.client:
            print("Error: Slack client not initialized")
            return False
        
        try:
            kwargs = {"channel": channel, "text": text}
            if blocks:
                kwargs["blocks"] = blocks
            
            response = self.client.chat_postMessage(**kwargs)
            return response["ok"]
        except SlackApiError as e:
            print(f"Error sending Slack message: {e}")
            return False
    
    def send_ephemeral_message(self, channel: str, user: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Send ephemeral message to user in channel."""
        if not self.client:
            print("Error: Slack client not initialized")
            return False
        
        try:
            kwargs = {"channel": channel, "user": user, "text": text}
            if blocks:
                kwargs["blocks"] = blocks
            
            response = self.client.chat_postEphemeral(**kwargs)
            return response["ok"]
        except SlackApiError as e:
            print(f"Error sending ephemeral message: {e}")
            return False
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        if not self.client:
            print("Error: Slack client not initialized")
            return None
        
        try:
            response = self.client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
            return None
        except SlackApiError as e:
            print(f"Error getting user info: {e}")
            return None
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information."""
        if not self.client:
            print("Error: Slack client not initialized")
            return None
        
        try:
            response = self.client.conversations_info(channel=channel_id)
            if response["ok"]:
                return response["channel"]
            return None
        except SlackApiError as e:
            print(f"Error getting channel info: {e}")
            return None
    
    def get_channel_members(self, channel_id: str) -> List[str]:
        """Get list of channel member IDs."""
        if not self.client:
            print("Error: Slack client not initialized")
            return []
        
        try:
            response = self.client.conversations_members(channel=channel_id)
            if response["ok"]:
                return response["members"]
            return []
        except SlackApiError as e:
            print(f"Error getting channel members: {e}")
            return []
    
    def create_modal(self, trigger_id: str, modal_data: Dict[str, Any]) -> bool:
        """Open a modal in Slack."""
        if not self.client:
            print("Error: Slack client not initialized")
            return False
        
        try:
            response = self.client.views_open(trigger_id=trigger_id, view=modal_data)
            return response["ok"]
        except SlackApiError as e:
            print(f"Error opening modal: {e}")
            return False
    
    def update_message(self, channel: str, ts: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Update an existing message."""
        if not self.client:
            print("Error: Slack client not initialized")
            return False
        
        try:
            kwargs = {"channel": channel, "ts": ts, "text": text}
            if blocks:
                kwargs["blocks"] = blocks
            
            response = self.client.chat_update(**kwargs)
            return response["ok"]
        except SlackApiError as e:
            print(f"Error updating message: {e}")
            return False 

    def respond_to_interaction(self, response_url: str, payload: Dict[str, Any]) -> bool:
        """Send a response to a Slack interaction via response_url (supports replace_original to keep loading state)."""
        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(response_url, json=payload, headers=headers, timeout=5)
            if resp.status_code != 200:
                print(f"Error responding to interaction: {resp.status_code} - {resp.text}")
                return False
            return True
        except Exception as e:
            print(f"Error sending interaction response: {e}")
            return False