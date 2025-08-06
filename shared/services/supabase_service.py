"""
Supabase service for database operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
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
    
    def store_filtered_transcript(self, filtered_transcript: str, pii_removed_count: int = 0, original_transcript: str = "", filename: str = "unknown.txt", replace_existing: bool = False) -> Optional[str]:
        """Store filtered transcript in Supabase using the new table structure with duplicate prevention."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            import hashlib
            
            # Simple filename-based duplicate prevention
            # If same filename exists, block processing (replace option available)
            
            # Try new schema first (with filename column), fallback to basic schema
            try:
                # Check if this filename already exists
                existing_filename = self.client.table('filtered_transcripts').select('id, filename, created_at').eq('filename', filename).execute()
                
                if existing_filename.data:
                    existing_record = existing_filename.data[0]
                    existing_date = existing_record.get('created_at', 'unknown')[:19] if existing_record.get('created_at') else 'unknown'
                    existing_id = existing_record['id']
                    
                    if replace_existing:
                        print(f"   🔄 File already processed: {filename}")
                        print(f"   📅 Previous processing: {existing_date}")
                        print(f"   🔁 Replacing existing record...")
                        
                        # Create updated data
                        content_hash = hashlib.md5(f"{original_transcript}||{filtered_transcript}".encode()).hexdigest()
                        original_hash = hashlib.md5(original_transcript.encode()).hexdigest()
                        
                        update_data = {
                            'filtered_transcript': filtered_transcript,
                            'pii_removed_count': pii_removed_count,
                            'content_hash': content_hash,
                            'original_hash': original_hash,
                            'original_length': len(original_transcript),
                            'filtered_length': len(filtered_transcript)
                        }
                        
                        # Update existing record
                        update_response = self.client.table('filtered_transcripts').update(update_data).eq('id', existing_id).execute()
                        
                        if update_response.data:
                            print(f"   ✅ Updated existing record: {existing_id}")
                            return existing_id
                        else:
                            print(f"   ⚠️  Failed to update existing record")
                            return existing_id  # Return original ID even if update failed
                    else:
                        print(f"   ⚠️  File already processed: {filename}")
                        print(f"   📅 Previous processing: {existing_date}")
                        print(f"   🔄 Returning existing record (no reprocessing needed)")
                        return existing_id
                
                # Create content hash for record keeping (optional)
                content_hash = hashlib.md5(f"{original_transcript}||{filtered_transcript}".encode()).hexdigest()
                original_hash = hashlib.md5(original_transcript.encode()).hexdigest()
                
                # Store new transcript with full content and metadata (new schema)
                data = {
                    'filtered_transcript': filtered_transcript,
                    'pii_removed_count': pii_removed_count,
                    'content_hash': content_hash,  # For potential future use
                    'original_hash': original_hash,  # For potential future use
                    'filename': filename,
                    'original_length': len(original_transcript),
                    'filtered_length': len(filtered_transcript)
                }
                
                response = self.client.table('filtered_transcripts').insert(data).execute()
                if response.data:
                    return response.data[0].get('id')
                
            except Exception as schema_error:
                if 'does not exist' in str(schema_error):
                    print(f"   💡 Using basic schema (filename column not found)")
                    
                    # Fallback to basic duplicate check using filtered content match
                    # This is less ideal but works for old schema
                    existing_basic = self.client.table('filtered_transcripts').select('id').eq('filtered_transcript', filtered_transcript).execute()
                    
                    if existing_basic.data:
                        print(f"   ⚠️  Identical content already exists (filename tracking unavailable)")
                        return existing_basic.data[0]['id']
                    
                    # Store with basic schema (fallback)
                    basic_data = {
                        'filtered_transcript': filtered_transcript,
                        'pii_removed_count': pii_removed_count
                    }
                    
                    response = self.client.table('filtered_transcripts').insert(basic_data).execute()
                    if response.data:
                        return response.data[0].get('id')
                else:
                    raise schema_error
            
            return None
        except Exception as e:
            print(f"Error storing filtered transcript: {e}")
            return None
    
    def get_filtered_transcript(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve filtered transcript by ID from the new table structure."""
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
    
    def get_recent_filtered_transcripts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently filtered transcripts from the new table."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return []
        
        try:
            response = self.client.table('filtered_transcripts').select('*').order('created_at', desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            print(f"Error retrieving recent filtered transcripts: {e}")
            return []
    
    def get_transcripts_by_filename(self, filename: str) -> List[Dict[str, Any]]:
        """Get all transcript variations for a specific filename."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return []
        
        try:
            response = self.client.table('filtered_transcripts').select('*').eq('filename', filename).order('created_at', desc=True).execute()
            return response.data or []
        except Exception as e:
            print(f"Error retrieving transcripts by filename: {e}")
            return []
    
    def check_if_filename_exists(self, filename: str) -> Optional[Dict[str, Any]]:
        """Check if a filename has already been processed."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('filtered_transcripts').select('*').eq('filename', filename).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error checking filename: {e}")
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
    
    def get_recent_transcripts(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get most recent transcripts ordered by creation date."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return []
        
        try:
            response = self.client.table('filtered_transcripts').select('*').order('created_at', desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            print(f"Error retrieving recent transcripts: {e}")
            return []
    
    def get_transcript_by_id(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific transcript by ID."""
        if not self.client:
            print("Error: Supabase client not initialized")
            return None
        
        try:
            response = self.client.table('filtered_transcripts').select('*').eq('id', transcript_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error retrieving transcript by ID: {e}")
            return None
    
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