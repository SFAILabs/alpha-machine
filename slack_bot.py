#!/usr/bin/env python3
"""
Slack bot entry point for Alpha Machine.
Handles slash commands and interactions.
"""

import sys
from pathlib import Path
from flask import Flask, request

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.flows.slack_flow.bot import SlackBot


def main():
    """Run the Slack bot server."""
    print("Starting Alpha Machine Slack Bot...")
    
    app = Flask(__name__)
    slack_bot = SlackBot()
    handler = slack_bot.get_handler()
    
    @app.route("/slack/events", methods=["POST"])
    def slack_events():
        """Handle Slack events."""
        return handler.handle(request)
    
    print("Slack bot server running on port 3000")
    app.run(host='0.0.0.0', port=3000)


if __name__ == "__main__":
    main() 