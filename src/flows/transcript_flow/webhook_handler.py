"""
Webhook handler for receiving Krisp transcripts via Zapier.
"""

from typing import Dict, Any
from flask import Flask, request, jsonify
from .processor import TranscriptProcessor


class WebhookHandler:
    """Handler for webhook requests from Zapier."""
    
    def __init__(self):
        """Initialize the webhook handler."""
        self.processor = TranscriptProcessor()
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/webhook/transcript', methods=['POST'])
        def handle_transcript_webhook():
            """Handle incoming transcript webhook from Zapier."""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({"error": "No data received"}), 400
                
                # Extract transcript data from Zapier payload
                transcript = data.get('transcript')
                metadata = {
                    'source': 'krisp',
                    'meeting_id': data.get('meeting_id'),
                    'participants': data.get('participants', []),
                    'meeting_date': data.get('meeting_date'),
                    'duration': data.get('duration'),
                    'zapier_webhook_id': data.get('webhook_id')
                }
                
                if not transcript:
                    return jsonify({"error": "No transcript found in payload"}), 400
                
                # Process the transcript
                result = self.processor.process_transcript(transcript, metadata)
                
                if result['success']:
                    return jsonify({
                        "success": True,
                        "transcript_id": result['transcript_id'],
                        "message": "Transcript processed and stored successfully"
                    }), 200
                else:
                    return jsonify({
                        "success": False,
                        "error": result['error']
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Internal server error: {str(e)}"
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({"status": "healthy"}), 200
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the webhook server."""
        self.app.run(host=host, port=port, debug=debug)


def create_webhook_handler() -> WebhookHandler:
    """Create and return a webhook handler instance."""
    return WebhookHandler() 