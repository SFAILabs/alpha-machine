"""
Supabase manager for database operations across all flows.
"""

from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from shared.core.config import Config


class SupabaseService:
    """Service for Supabase database operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client with configuration."""
        if Config.SUPABASE_URL and Config.SUPABASE_KEY:
            self.client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        else:
            print("Warning: Supabase credentials not configured")
    
    def store_transcript(self, transcript_data: Dict[str, Any]) -> Optional[str]:
        """Store transcript in Supabase."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('transcripts').insert(transcript_data).execute()
            if response.data:
                return response.data[0].get('id')
            return None
        except Exception as e:
            print(f"Error storing transcript: {e}")
            return None
    
    def get_transcript(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve transcript by ID."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('transcripts').select('*').eq('id', transcript_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error retrieving transcript: {e}")
            return None
    
    def get_transcripts_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get transcripts within a date range."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return []
        
        try:
            response = self.client.table('transcripts').select('*').gte('created_at', start_date).lte('created_at', end_date).execute()
            return response.data or []
        except Exception as e:
            print(f"Error retrieving transcripts by date range: {e}")
            return []
    
    def update_transcript(self, transcript_id: str, updates: Dict[str, Any]) -> bool:
        """Update transcript with new data."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return False
        
        try:
            response = self.client.table('transcripts').update(updates).eq('id', transcript_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating transcript: {e}")
            return False
    
    def store_meeting_summary(self, summary_data: Dict[str, Any]) -> Optional[str]:
        """Store meeting summary in Supabase."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('meeting_summaries').insert(summary_data).execute()
            if response.data:
                return response.data[0].get('id')
            return None
        except Exception as e:
            print(f"Error storing meeting summary: {e}")
            return None
    
    def get_client_status(self, client_name: str) -> Optional[Dict[str, Any]]:
        """Get client status information."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('client_status').select('*').eq('client_name', client_name).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error retrieving client status: {e}")
            return None
    
    def store_filtered_transcript(self, filtered_transcript_data: Dict[str, Any]) -> Optional[str]:
        """Store filtered transcript in Supabase."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('filtered_transcripts').insert(filtered_transcript_data).execute()
            if response.data:
                return response.data[0].get('id')
            return None
        except Exception as e:
            print(f"Error storing filtered transcript: {e}")
            return None
    
    def get_filtered_transcript(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve filtered transcript by ID."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('filtered_transcripts').select('*').eq('id', transcript_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error retrieving filtered transcript: {e}")
            return None
    
    def get_filtered_transcripts_by_project(self, project_name: str) -> List[Dict[str, Any]]:
        """Get filtered transcripts by project tag."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return []
        
        try:
            response = self.client.table('filtered_transcripts').select('*').contains('project_tags', [project_name]).execute()
            return response.data or []
        except Exception as e:
            print(f"Error retrieving filtered transcripts by project: {e}")
            return []
    
    def get_filtered_transcripts_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get filtered transcripts within a date range."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return []
        
        try:
            response = self.client.table('filtered_transcripts').select('*').gte('meeting_date', start_date).lte('meeting_date', end_date).execute()
            return response.data or []
        except Exception as e:
            print(f"Error retrieving filtered transcripts by date range: {e}")
            return []
    
    def update_filtered_transcript(self, transcript_id: str, updates: Dict[str, Any]) -> bool:
        """Update filtered transcript with new data."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return False
        
        try:
            response = self.client.table('filtered_transcripts').update(updates).eq('id', transcript_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating filtered transcript: {e}")
            return False
    
    def delete_filtered_transcript(self, transcript_id: str) -> bool:
        """Delete filtered transcript by ID."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return False
        
        try:
            response = self.client.table('filtered_transcripts').delete().eq('id', transcript_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting filtered transcript: {e}")
            return False 
    
    def store_chat_session(self, session_data: Dict[str, Any]) -> bool:
        """Store chat session data."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return False
        
        try:
            # Upsert to handle both insert and update
            response = self.client.table('chat_sessions').upsert(session_data).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error storing chat session: {e}")
            return False
    
    def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session by ID."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('chat_sessions').select('*').eq('session_id', session_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error retrieving chat session: {e}")
            return None
    
    def delete_chat_session(self, session_id: str) -> bool:
        """Delete chat session by ID."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return False
        
        try:
            response = self.client.table('chat_sessions').delete().eq('session_id', session_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting chat session: {e}")
            return False 