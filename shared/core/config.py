"""
Configuration management for Alpha Machine.
"""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


class Config:
    """Configuration class for managing environment variables and settings."""
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    SRC_DIR = PROJECT_ROOT / "src"
    DATA_DIR = PROJECT_ROOT / "data"
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "16000"))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
    
    # Linear Configuration
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    TEST_LINEAR_API_KEY = os.getenv("TEST_LINEAR_API_KEY")
    LINEAR_TEAM_NAME = os.getenv("LINEAR_TEAM_NAME", "Jonathan Test Space")
    LINEAR_DEFAULT_ASSIGNEE = os.getenv("LINEAR_DEFAULT_ASSIGNEE", "jonny34923@gmail.com")
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # Slack Configuration
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")
    SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")
    
    # Notion Configuration
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    
    # File paths
    PROMPTS_FILE = Path(__file__).parent / "prompts.yml"
    TRANSCRIPT_FILE = PROJECT_ROOT / "sfai_dev_standup_transcript.txt"
    OUTPUT_FILE = PROJECT_ROOT / "generated_tickets.json"
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required environment variables are set."""
        required_vars = {
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    @classmethod
    def get_openai_config(cls) -> Dict[str, Any]:
        """Get OpenAI configuration as a dictionary."""
        return {
            "api_key": cls.OPENAI_API_KEY,
            "model": cls.OPENAI_MODEL,
            "max_tokens": cls.OPENAI_MAX_TOKENS,
            "temperature": cls.OPENAI_TEMPERATURE
        }
    
    @classmethod
    def get_linear_config(cls) -> Dict[str, Any]:
        """Get Linear configuration for SFAI workspace (READ ONLY)."""
        return {
            "api_key": cls.LINEAR_API_KEY,
            "team_name": cls.LINEAR_TEAM_NAME,
            "default_assignee": cls.LINEAR_DEFAULT_ASSIGNEE
        }
    
    @classmethod
    def get_test_linear_config(cls) -> Dict[str, Any]:
        """Get Linear configuration for Jonathan Test Space (WRITE ONLY)."""
        return {
            "api_key": cls.TEST_LINEAR_API_KEY,
            "team_name": cls.LINEAR_TEAM_NAME,
            "default_assignee": cls.LINEAR_DEFAULT_ASSIGNEE
        } 