"""
Alpha Machine - AI-powered transcript processing and project management.

A sophisticated internal tool for processing meeting transcripts, managing Linear tickets,
and providing AI-powered Slack bot functionality.
"""

__version__ = "0.1.0"
__author__ = "Alpha Machine Team"

# Core components
from .core.config import Config
from .core.models import (
    LinearProject, LinearMilestone, LinearIssue, LinearContext,
    GeneratedIssue, GeneratedIssuesResponse, ProcessingResult
)
from .core.utils import print_separator, load_prompts

# Services
from .services.ai_service import OpenAIService
from .services.supabase_service import SupabaseService
from .services.linear_service import LinearService
from .services.slack_service import SlackService
from .services.notion_service import NotionService
from .services.transcript_service import TranscriptService

# Flows
from .flows.transcript_flow import TranscriptProcessor, WebhookHandler, create_webhook_handler
from .flows.slack_flow import SlackBot
from .flows.linear_flow import AlphaMachineOrchestrator
from .flows.notion_flow import NotionProcessor

__all__ = [
    # Core
    "Config", "print_separator", "load_prompts",
    # Models
    "LinearProject", "LinearMilestone", "LinearIssue", "LinearContext",
    "GeneratedIssue", "GeneratedIssuesResponse", "ProcessingResult",
    # Services
    "OpenAIService", "SupabaseService", "LinearService", "SlackService", "NotionService", "TranscriptService",
    # Flows
    "TranscriptProcessor", "WebhookHandler", "create_webhook_handler",
    "SlackBot", "AlphaMachineOrchestrator", "NotionProcessor"
] 