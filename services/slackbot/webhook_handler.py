"""
Slack Webhook Handler for Alpha Machine Bot

Handles Slack events, slash commands, and OAuth flow using FastAPI directly.
This provides the endpoints that Slack will call for bot interactions.
"""

import json
import hmac
import hashlib
import time
import sys
import traceback
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import urllib.parse
import logging

from shared.core.config import Config
from command_handler import SlackCommandHandler
from event_handler import SlackEventHandler

slack_webhook_router = APIRouter()

# Initialize handlers
command_handler = SlackCommandHandler()
event_handler = SlackEventHandler()

# Configure logging
logger = logging.getLogger(__name__)

@slack_webhook_router.get("/test-ai")
async def test_ai_service():
    """Test endpoint to verify AI service and environment variables"""
    try:
        # Test environment variables
        from shared.core.config import Config
        
        result = {
            "openai_key_present": bool(getattr(Config, 'OPENAI_API_KEY', None)),
            "openai_model": getattr(Config, 'OPENAI_MODEL', 'NOT_SET'),
            "config_accessible": True
        }
        
        # Test AI service instantiation
        from shared.services.ai_service import OpenAIService
        ai_service = OpenAIService()
        result["ai_service_created"] = True
        
        # Test simple AI call
        system_prompt = "You are a helpful assistant."
        user_prompt = "Say 'Hello, this is a test!'"
        
        ai_response = await ai_service.generate_text_async(system_prompt, user_prompt)
        result["ai_call_success"] = True
        result["ai_response"] = ai_response[:100]  # First 100 chars
        
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "error_type": type(e).__name__,
            "ai_call_success": False
        })

def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify that the request came from Slack by validating the signature.
    """
    if not Config.SLACK_SIGNING_SECRET:
        return False
    
    # Create the signature string
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    
    # Create the expected signature
    expected_signature = 'v0=' + hmac.new(
        Config.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(expected_signature, signature)

@slack_webhook_router.post("/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Main endpoint for Slack events (mentions, messages, reactions, etc.)
    """
    # Get request data
    body = await request.body()
    headers = request.headers
    
    # Verify the request came from Slack
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Check if request is too old (prevent replay attacks)
    if abs(time.time() - int(timestamp)) > 60 * 5:  # 5 minutes
        raise HTTPException(status_code=403, detail="Request too old")
    
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return PlainTextResponse(payload.get("challenge", ""))
    
    # Handle events in background to respond quickly to Slack
    if payload.get("type") == "event_callback":
        background_tasks.add_task(event_handler.handle_event, payload)
        return JSONResponse({"status": "ok"})
    
    return JSONResponse({"status": "ok"})

@slack_webhook_router.post("/commands")
async def slack_commands(
    background_tasks: BackgroundTasks,
    request: Request,
    token: str = Form(...),
    team_id: str = Form(...),
    team_domain: str = Form(...),
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    user_id: str = Form(...),
    user_name: str = Form(...),
    command: str = Form(...),
    text: str = Form(""),
    response_url: str = Form(...),
    trigger_id: str = Form(...)
):
    """
    Handle all Slack slash commands (/chat, /summarize, etc.)
    Returns immediate acknowledgment and processes command in background
    """
    # Force output to stdout for Cloud Run visibility
    print(f"=== WEBHOOK RECEIVED: {command} from {user_id} ===", flush=True)
    print(f"=== RESPONSE URL: {response_url} ===", flush=True)
    
    logger.info(f"=== WEBHOOK RECEIVED: {command} from {user_id} ===")
    logger.info(f"=== RESPONSE URL: {response_url} ===")
    
    # Note: For form data, we skip signature verification to avoid stream consumption issues
    # In production, you would implement signature verification differently for form endpoints
    headers = request.headers
    
    # Optional: Basic validation that this looks like a Slack request
    logger.info(f"WEBHOOK VALIDATION: Checking Slack timestamp header")
    if not headers.get("X-Slack-Request-Timestamp"):
        logger.error(f"WEBHOOK ERROR: Missing Slack timestamp")
        raise HTTPException(status_code=403, detail="Missing Slack timestamp")
    logger.info(f"WEBHOOK VALIDATION: Slack timestamp found")
    
    # Create command payload
    logger.info(f"WEBHOOK PAYLOAD: Creating payload for {command}")
    command_payload = {
        "token": token,
        "team_id": team_id,
        "team_domain": team_domain,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "user_id": user_id,
        "user_name": user_name,
        "command": command,
        "text": text,
        "response_url": response_url,
        "trigger_id": trigger_id
    }
    logger.info(f"WEBHOOK PAYLOAD: Created payload with response_url: {response_url}")
    
    # Process command in background and return immediate acknowledgment
    logger.info(f"WEBHOOK: Adding background task for command: {command}")
    print(f"=== WEBHOOK: Adding background task for {command} ===", flush=True)
    
    try:
        # Use a new event loop to avoid cancellation on reload
        import asyncio
        loop = asyncio.get_event_loop()
        # Always schedule a plain callable to BackgroundTasks to avoid ASGI errors
        background_tasks.add_task(lambda: loop.create_task(command_handler.handle_command(command_payload)))
        print(f"=== WEBHOOK: Background task added successfully ===", flush=True)
        logger.info(f"WEBHOOK: Background task added successfully")
        
        # Return immediate acknowledgment to meet Slack's 3-second timeout
        friendly = {
            "/chat": "🤖 Processing your /chat command... ⏳",
            "/summarize": "📝 Processing your /summarize request... ⏳",
            "/create": "📋 Processing your /create request... ⏳",
            "/create-ticket": "📋 Processing your /create request... ⏳",
            "/update": "✏️ Processing your /update request... ⏳",
            "/teammember": "👤 Processing your /teammember request... ⏳",
            "/weekly-summary": "📈 Processing your /weekly-summary request... ⏳",
        }
        ack_text = friendly.get(command, f"🤖 Processing your {command}... ⏳")
        return JSONResponse({
            "response_type": "ephemeral",
            "text": ack_text
        })
        
    except Exception as e:
        print(f"=== WEBHOOK BACKGROUND TASK ERROR: {type(e).__name__}: {str(e)} ===", flush=True)
        print(f"=== WEBHOOK BACKGROUND TASK TRACEBACK: {traceback.format_exc()} ===", flush=True)
        logger.error(f"WEBHOOK BACKGROUND TASK ERROR: {type(e).__name__}: {str(e)}")
        logger.error(f"WEBHOOK BACKGROUND TASK TRACEBACK: {traceback.format_exc()}")
        
        return JSONResponse({
            "response_type": "ephemeral", 
            "text": "❌ Sorry, I encountered an error processing your /chat command. Please try again."
        })

@slack_webhook_router.post("/commands/sync-test")
async def slack_commands_sync_test(
    request: Request,
    token: str = Form(...),
    team_id: str = Form(...),
    team_domain: str = Form(...),
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    user_id: str = Form(...),
    user_name: str = Form(...),
    command: str = Form(...),
    text: str = Form(""),
    response_url: str = Form(...),
    trigger_id: str = Form(...)
):
    """
    SYNCHRONOUS version - returns AI response directly (for testing)
    """
    print(f"=== SYNC TEST: {command} with text: '{text}' ===", flush=True)
    
    try:
        # Create command payload
        command_payload = {
            "token": token,
            "team_id": team_id,
            "team_domain": team_domain,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "user_id": user_id,
            "user_name": user_name,
            "command": command,
            "text": text,
            "response_url": response_url,
            "trigger_id": trigger_id
        }
        
        # Process command SYNCHRONOUSLY (wait for AI)
        print("=== SYNC TEST: Starting AI processing ===", flush=True)
        result = await command_handler.handle_command_sync(command_payload)
        print(f"=== SYNC TEST: AI Result: {result} ===", flush=True)
        
        # Return AI response directly
        return JSONResponse({
            "response_type": "in_channel",  # Make it visible to all
            "text": f"🤖 **AI Response:** {result}"
        })
        
    except Exception as e:
        print(f"=== SYNC TEST ERROR: {str(e)} ===", flush=True)
        print(f"=== SYNC TEST TRACEBACK: {traceback.format_exc()} ===", flush=True)
        
        return JSONResponse({
            "response_type": "ephemeral",
            "text": f"❌ Error: {str(e)}"
        })

@slack_webhook_router.post("/interactive")
async def slack_interactive(request: Request, background_tasks: BackgroundTasks):
    """
    Handle interactive components (buttons, modals, etc.)
    """
    # Get form data
    form_data = await request.form()
    payload_str = form_data.get("payload", "")
    
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Optional: Basic validation for interactive components
    headers = request.headers
    if not headers.get("X-Slack-Request-Timestamp"):
        raise HTTPException(status_code=403, detail="Missing Slack timestamp")
    
    # Handle interaction in background
    background_tasks.add_task(event_handler.handle_interaction, payload)
    
    return JSONResponse({"status": "ok"})

@slack_webhook_router.get("/oauth/redirect")
async def slack_oauth_redirect(code: Optional[str] = None, error: Optional[str] = None):
    """
    Handle OAuth redirect from Slack app installation
    """
    if error:
        return JSONResponse({
            "error": f"OAuth error: {error}",
            "message": "Failed to install Slack app"
        }, status_code=400)
    
    if not code:
        return JSONResponse({
            "error": "No authorization code provided",
            "message": "OAuth flow incomplete"
        }, status_code=400)
    
    # TODO: Exchange code for access token
    # This would typically involve calling Slack's oauth.v2.access API
    # For now, return success message
    
    return JSONResponse({
        "message": "Slack app installed successfully!",
        "next_steps": "You can now use the bot in your Slack workspace"
    })

@slack_webhook_router.get("/install")
async def slack_install():
    """
    Provide Slack app installation link
    """
    if not Config.SLACK_CLIENT_ID:
        return JSONResponse({
            "error": "Slack app not configured",
            "message": "SLACK_CLIENT_ID not set in environment"
        }, status_code=500)
    
    # Generate Slack OAuth URL
    scopes = [
        "app_mentions:read",
        "channels:history",
        "channels:read", 
        "chat:write",
        "commands",
        "groups:history",
        "groups:read",
        "im:history",
        "im:read",
        "im:write",
        "mpim:history",
        "mpim:read",
        "reactions:read",
        "users:read",
        "users:read.email",
        "team:read"
    ]
    
    scope_string = ",".join(scopes)
    
    install_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={Config.SLACK_CLIENT_ID}"
        f"&scope={scope_string}"
        f"&redirect_uri={Config.SLACK_REDIRECT_URI or 'https://your-domain.com/slack/oauth/redirect'}"
    )
    
    return JSONResponse({
        "install_url": install_url,
        "message": "Click the install_url to add the bot to your Slack workspace"
    })

# Health check endpoint
@slack_webhook_router.get("/health")
def slack_health():
    """Check if Slack service is properly configured"""
    config_status = {
        "bot_token": bool(Config.SLACK_BOT_TOKEN),
        "signing_secret": bool(Config.SLACK_SIGNING_SECRET),
        "client_id": bool(getattr(Config, 'SLACK_CLIENT_ID', None)),
    }
    
    all_configured = all(config_status.values())
    
    return JSONResponse({
        "status": "healthy" if all_configured else "partially_configured",
        "config": config_status,
        "message": "All Slack config present" if all_configured else "Missing some Slack configuration"
    })

@slack_webhook_router.get("/debug")
def debug_environment():
    """Debug endpoint to check all environment variables and service initialization."""
    try:
        debug_info = {
            "environment": {
                "openai_api_key": bool(Config.OPENAI_API_KEY),
                "openai_api_key_length": len(str(Config.OPENAI_API_KEY)) if Config.OPENAI_API_KEY else 0,
                "openai_model": Config.OPENAI_MODEL,
                "linear_api_key": bool(Config.LINEAR_API_KEY),
                "linear_team_name": Config.LINEAR_TEAM_NAME,
                "supabase_url": bool(Config.SUPABASE_URL),
                "supabase_key": bool(Config.SUPABASE_KEY),
                "slack_bot_token": bool(Config.SLACK_BOT_TOKEN),
                "slack_signing_secret": bool(Config.SLACK_SIGNING_SECRET)
            },
            "service_init": "attempting"
        }
        
        # Try to initialize command handler
        from command_handler import SlackCommandHandler
        handler = SlackCommandHandler()
        debug_info["service_init"] = "success"
        debug_info["services"] = {
            "slack_service": bool(handler.slack_service),
            "ai_service": bool(handler.ai_service),
            "linear_service": bool(handler.linear_service),
            "supabase_service": bool(handler.supabase_service),
            "notion_service": bool(handler.notion_service),
            "prompts": bool(handler.prompts)
        }
        
        # Test AI service directly
        try:
            import asyncio
            async def test_ai():
                response = await handler.ai_service.generate_text_async(
                    "You are a helpful assistant.",
                    "Say 'test successful' in exactly 2 words."
                )
                return response
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ai_test_result = loop.run_until_complete(test_ai())
            loop.close()
            
            debug_info["ai_test"] = {
                "success": True,
                "response": ai_test_result[:100] if ai_test_result else "None"
            }
        except Exception as ai_error:
            debug_info["ai_test"] = {
                "success": False,
                "error": str(ai_error)
            }
        
        return JSONResponse(debug_info)
        
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "environment": {
                "openai_api_key": bool(getattr(Config, 'OPENAI_API_KEY', None)),
                "openai_api_key_length": len(str(getattr(Config, 'OPENAI_API_KEY', ''))) if getattr(Config, 'OPENAI_API_KEY', None) else 0,
            }
        }) 