"""
Webhook handler for receiving Krisp transcripts via Zapier.
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from .processor import TranscriptProcessor

webhook_router = APIRouter()
processor = TranscriptProcessor()

@webhook_router.post("/transcript")
async def handle_transcript_webhook(request: Request):
    """Handle incoming transcript webhook from Zapier."""
    try:
        data = await request.json()
        
        if not data:
            raise HTTPException(status_code=400, detail="No data received")
        
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
            raise HTTPException(status_code=400, detail="No transcript found in payload")
        
        # Process the transcript
        result = processor.process_transcript(transcript, metadata)
        
        if result['success']:
            return {
                "success": True,
                "transcript_id": result['transcript_id'],
                "message": "Transcript processed and stored successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@webhook_router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 