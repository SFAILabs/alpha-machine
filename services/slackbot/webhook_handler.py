"""
Slack Webhook Handler for Alpha Machine Bot

Handles Slack events, slash commands, and OAuth flow using FastAPI directly.
This provides the endpoints that Slack will call for bot interactions.
"""

import json
import hmac
import hashlib
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
import urllib.parse

from shared.core.config import Config
from .command_handler import SlackCommandHandler
from .event_handler import SlackEventHandler

slack_webhook_router = APIRouter()

# Initialize handlers
command_handler = SlackCommandHandler()
event_handler = SlackEventHandler()

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
    request: Request,
    background_tasks: BackgroundTasks,
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
    """
    # Get request data for signature verification
    body = await request.body()
    headers = request.headers
    
    # Verify the request came from Slack
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
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
    
    # Handle command in background and return immediate response
    background_tasks.add_task(command_handler.handle_command, command_payload)
    
    # Return immediate acknowledgment
    return JSONResponse({
        "response_type": "ephemeral",
        "text": f"Processing your {command} command... ⏳"
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
    
    # Verify the request came from Slack
    body = f"payload={urllib.parse.quote(payload_str)}".encode()
    headers = request.headers
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
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