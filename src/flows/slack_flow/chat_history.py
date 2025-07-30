"""
Chat history service using OpenAI Responses API with previous_response_id.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from ...services.supabase_service import SupabaseService


class ChatHistoryService:
    """Chat history service using OpenAI Responses API with previous_response_id."""
    
    def __init__(self):
        """Initialize the chat history service."""
        self.supabase_service = SupabaseService()
    
    def get_previous_response_id(self, user_id: str, channel_id: str) -> Optional[str]:
        """Get the previous response ID for a user/channel conversation."""
        session_id = f"{user_id}_{channel_id}"
        
        try:
            data = self.supabase_service.get_chat_session(session_id)
            return data.get('previous_response_id') if data else None
        except Exception as e:
            print(f"Error getting previous response ID: {e}")
            return None
    
    def store_previous_response_id(self, user_id: str, channel_id: str, response_id: str) -> bool:
        """Store the previous response ID for a user/channel conversation."""
        session_id = f"{user_id}_{channel_id}"
        
        try:
            return self.supabase_service.store_chat_session({
                'session_id': session_id,
                'user_id': user_id,
                'channel_id': channel_id,
                'previous_response_id': response_id,
                'updated_at': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error storing previous response ID: {e}")
            return False
    
    def clear_conversation(self, user_id: str, channel_id: str) -> bool:
        """Clear conversation history by removing previous_response_id."""
        session_id = f"{user_id}_{channel_id}"
        
        try:
            return self.supabase_service.delete_chat_session(session_id)
        except Exception as e:
            print(f"Error clearing conversation: {e}")
            return False
    
    def get_session_info(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Get session information."""
        session_id = f"{user_id}_{channel_id}"
        
        try:
            data = self.supabase_service.get_chat_session(session_id)
            if data:
                return {
                    "session_id": session_id,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "previous_response_id": data.get('previous_response_id'),
                    "updated_at": data.get('updated_at'),
                    "has_conversation": bool(data.get('previous_response_id'))
                }
            return {
                "session_id": session_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "previous_response_id": None,
                "has_conversation": False
            }
        except Exception as e:
            print(f"Error getting session info: {e}")
            return {"error": str(e)} 