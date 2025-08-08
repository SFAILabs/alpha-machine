import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

logger.info("=== SLACKBOT MAIN STARTING UP ===")

from webhook_handler import slack_webhook_router

app = FastAPI(title="Alpha Machine Slackbot", version="1.0.0")

logger.info("=== FASTAPI APP CREATED ===")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(slack_webhook_router, prefix="/slack")

logger.info("=== ROUTER INCLUDED ===")

@app.get("/")
def read_root():
    logger.info("=== ROOT ENDPOINT CALLED ===")
    return {"Service": "Slackbot", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
def health_check():
    logger.info("=== HEALTH ENDPOINT CALLED ===")
    return {"status": "healthy", "service": "slackbot"}

@app.get("/debug")
async def debug_ai():
    """Debug endpoint to test AI service"""
    try:
        # Test imports and config
        from shared.core.config import Config
        from shared.services.ai_service import OpenAIService
        
        result = {
            "status": "healthy",
            "service": "slackbot",
            "openai_key_present": bool(getattr(Config, 'OPENAI_API_KEY', None)),
            "openai_model": getattr(Config, 'OPENAI_MODEL', 'NOT_SET'),
            "imports_ok": True
        }
        
        # Test AI service
        ai_service = OpenAIService()
        ai_response = await ai_service.generate_text_async(
            "You are a helpful assistant.", 
            "Say 'Test successful!'"
        )
        
        result["ai_test"] = "SUCCESS"
        result["ai_response"] = ai_response[:50]
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

if __name__ == "__main__":
    logger.info("=== STARTING UVICORN SERVER ===")
    # Disable reload in production to avoid extra workers shutting down background tasks
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)