#!/usr/bin/env python3
"""
FastAPI server for Alpha Machine transcript processing.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
from pathlib import Path
import tempfile
import os
from datetime import datetime
from typing import Optional

# Import our services
from . import TranscriptFilterService, Config


app = FastAPI(
    title="Alpha Machine API",
    description="AI-powered transcript processing and management system",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Alpha Machine API is running", "status": "healthy"}


@app.post("/api/process-transcript")
async def process_transcript(
    file: UploadFile = File(...),
    meeting_date: Optional[str] = None
):
    """
    Process a transcript file through AI filtering and store in Supabase.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are supported")
        
        # Read the transcript content
        transcript_content = await file.read()
        transcript_text = transcript_content.decode('utf-8')
        
        # Parse meeting date if provided
        parsed_meeting_date = None
        if meeting_date:
            try:
                parsed_meeting_date = datetime.fromisoformat(meeting_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid meeting_date format. Use YYYY-MM-DD")
        
        # Use the existing service to process and store
        filter_service = TranscriptFilterService()
        stored_id = filter_service.process_and_store_transcript(
            transcript_text,
            file.filename,
            parsed_meeting_date
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Transcript processed and stored successfully",
                "data": {"stored_id": stored_id}
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error processing transcript: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Alpha Machine Transcript Processor",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    # Run the server
    print("🚀 Starting Alpha Machine API server...")
    print(f"📡 Server will be available at: http://localhost:8000")
    print(f"📚 API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 