#!/usr/bin/env python3
"""
Webhook server for transcript flow.
Handles incoming transcripts from Krisp via Zapier.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.flows.transcript_flow.webhook_handler import create_webhook_handler


def main():
    """Run the webhook server."""
    print("Starting Alpha Machine Webhook Server...")
    print("Listening for transcript webhooks from Krisp/Zapier")
    
    handler = create_webhook_handler()
    handler.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    main() 