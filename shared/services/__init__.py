"""
Alpha Machine Services Package
Contains shared service clients for external APIs.
"""

from .ai_service import OpenAIService
from .linear_service import LinearService
from .slack_service import SlackService
from .notion_service import NotionService
from .supabase_service import SupabaseService

__version__ = "0.1.0"
__all__ = [
    "OpenAIService",
    "LinearService", 
    "SlackService",
    "NotionService",
    "SupabaseService"
]
