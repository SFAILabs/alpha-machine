#!/usr/bin/env python3
"""
Automated Slack App Configuration Script for Alpha Machine Bot
Configures slash commands, events, and OAuth settings programmatically.
"""

import requests
import json
import os
import sys
from typing import Dict, List, Optional
from urllib.parse import urlencode


class SlackAppConfigurator:
    """Automates Slack app configuration for Alpha Machine Bot."""
    
    def __init__(self, app_token: Optional[str] = None):
        """Initialize with Slack app configuration token."""
        self.app_token = app_token or os.getenv('SLACK_APP_TOKEN')
        self.service_url = "https://slackbot-service-zyt7rmwq2a-uc.a.run.app"
        self.app_id = None
        
        if not self.app_token:
            print("⚠️  SLACK_APP_TOKEN not provided. Some features will be limited.")
    
    def create_app_manifest(self) -> Dict:
        """Generate Slack app manifest with all required configurations."""
        return {
            "display_information": {
                "name": "Alpha Machine Bot",
                "description": "AI-powered assistant for project management, meeting summaries, and team collaboration",
                "background_color": "#2c3e50",
                "long_description": "Alpha Machine Bot integrates with Linear, Supabase, and OpenAI to provide intelligent assistance for your team. Get meeting summaries, create and update tickets, track team member work, and chat with an AI that understands your project context."
            },
            "features": {
                "app_home": {
                    "home_tab_enabled": True,
                    "messages_tab_enabled": True
                },
                "bot_user": {
                    "display_name": "Alpha Machine",
                    "always_online": True
                },
                "slash_commands": [
                    {
                        "command": "/chat",
                        "url": f"{self.service_url}/slack/commands",
                        "description": "Chat with AI assistant about projects and work",
                        "usage_hint": "What are our current project priorities?",
                        "should_escape": False
                    },
                    {
                        "command": "/summarize",
                        "url": f"{self.service_url}/slack/commands",
                        "description": "Get meeting summaries or client status updates",
                        "usage_hint": "last meeting | client [client_name]",
                        "should_escape": False
                    },
                    {
                        "command": "/create",
                        "url": f"{self.service_url}/slack/commands",
                        "description": "Create Linear tickets with AI assistance",
                        "usage_hint": "Fix login bug with better error handling",
                        "should_escape": False
                    },
                    {
                        "command": "/update",
                        "url": f"{self.service_url}/slack/commands",
                        "description": "Update existing Linear tickets",
                        "usage_hint": "ABC-123 to in progress",
                        "should_escape": False
                    },
                    {
                        "command": "/teammember",
                        "url": f"{self.service_url}/slack/commands",
                        "description": "Get team member information and current work",
                        "usage_hint": "john@company.com",
                        "should_escape": False
                    },
                    {
                        "command": "/weekly-summary",
                        "url": f"{self.service_url}/slack/commands",
                        "description": "Generate comprehensive weekly team report",
                        "usage_hint": "(no parameters needed)",
                        "should_escape": False
                    }
                ]
            },
            "oauth_config": {
                "scopes": {
                    "bot": [
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
                }
            },
            "settings": {
                "event_subscriptions": {
                    "request_url": f"{self.service_url}/slack/events",
                    "bot_events": [
                        "app_mention",
                        "message.im",
                        "reaction_added",
                        "team_join"
                    ]
                },
                "interactivity": {
                    "is_enabled": True,
                    "request_url": f"{self.service_url}/slack/interactive"
                },
                "org_deploy_enabled": False,
                "socket_mode_enabled": False,
                "token_rotation_enabled": False
            }
        }
    
    def generate_manual_setup_commands(self) -> str:
        """Generate manual setup instructions and API calls."""
        manifest = self.create_app_manifest()
        
        setup_script = f"""
# Alpha Machine Bot - Manual Slack App Setup Instructions
# =====================================================

## 1. Create Slack App Using Manifest (Recommended)

Go to: https://api.slack.com/apps?new_app=1

Select "From an app manifest" and paste this JSON:

```json
{json.dumps(manifest, indent=2)}
```

## 2. Alternative: Manual Configuration Steps

If you prefer manual setup, go to https://api.slack.com/apps and:

### A. Create New App
- Name: "Alpha Machine Bot"
- Choose your workspace

### B. Configure Slash Commands
Add these commands (Features → Slash Commands):

"""
        
        for cmd in manifest["features"]["slash_commands"]:
            setup_script += f"""
Command: {cmd['command']}
Request URL: {cmd['url']}
Description: {cmd['description']}
Usage Hint: {cmd['usage_hint']}
"""
        
        setup_script += f"""

### C. Configure Event Subscriptions
(Features → Event Subscriptions)

Request URL: {manifest["settings"]["event_subscriptions"]["request_url"]}

Bot Events to Subscribe To:
"""
        
        for event in manifest["settings"]["event_subscriptions"]["bot_events"]:
            setup_script += f"- {event}\n"
        
        setup_script += f"""

### D. Configure Interactive Components
(Features → Interactivity & Shortcuts)

Request URL: {manifest["settings"]["interactivity"]["request_url"]}

### E. Set OAuth Scopes
(Features → OAuth & Permissions → Scopes)

Bot Token Scopes:
"""
        
        for scope in manifest["oauth_config"]["scopes"]["bot"]:
            setup_script += f"- {scope}\n"
        
        setup_script += """

### F. Install App
(Settings → Install App)
- Click "Install to Workspace"
- Copy the Bot User OAuth Token (starts with xoxb-)
- Copy the Signing Secret from Basic Information

## 3. Update Environment Variables

After installation, update your Cloud Run service:

```bash
# Update with your actual tokens
gcloud run services update slackbot-service \\
  --region=us-central1 \\
  --set-env-vars="SLACK_BOT_TOKEN=xoxb-your-token-here,SLACK_SIGNING_SECRET=your-signing-secret-here"
```

## 4. Test Integration

Run: python test_slack_integration.py

Then test these commands in Slack:
- /chat hello
- /summarize last meeting
- /teammember john
- /weekly-summary
- @Alpha Machine help
"""
        
        return setup_script
    
    def create_curl_commands(self) -> str:
        """Generate curl commands for API-based setup (if you have app tokens)."""
        commands = f"""
# Alpha Machine Bot - API Configuration Commands
# ============================================

# Note: These require SLACK_APP_TOKEN with admin permissions
# Most users should use the manifest method above instead

export SLACK_APP_TOKEN="your-app-config-token-here"
export APP_ID="your-app-id-here"

# Configure Event Subscriptions
curl -X POST https://slack.com/api/apps.event.subscriptions.update \\
  -H "Authorization: Bearer $SLACK_APP_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "app_id": "$APP_ID",
    "event_subscriptions": {{
      "enabled": true,
      "request_url": "{self.service_url}/slack/events",
      "bot_events": ["app_mention", "message.im", "reaction_added", "team_join"]
    }}
  }}'

# Configure Interactive Components  
curl -X POST https://slack.com/api/apps.interactivity.update \\
  -H "Authorization: Bearer $SLACK_APP_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "app_id": "$APP_ID",
    "interactivity": {{
      "enabled": true,
      "request_url": "{self.service_url}/slack/interactive"
    }}
  }}'

# Add Slash Commands (repeat for each command)
curl -X POST https://slack.com/api/apps.commands.create \\
  -H "Authorization: Bearer $SLACK_APP_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "app_id": "$APP_ID",
    "command": "/chat",
    "url": "{self.service_url}/slack/commands",
    "description": "Chat with AI assistant about projects and work",
    "usage_hint": "What are our current project priorities?"
  }}'
"""
        return commands
    
    def test_service_endpoints(self) -> bool:
        """Test that our service endpoints are working."""
        print("🔍 Testing Alpha Machine service endpoints...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.service_url}/slack/health", timeout=10)
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Health check: {health['status']}")
                
                # Check configuration
                config = health.get('config', {})
                print("   📊 Configuration status:")
                for key, configured in config.items():
                    status = "✅" if configured else "❌"
                    print(f"      {status} {key}: {'ready' if configured else 'needs setup'}")
                
                return True
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Service test failed: {e}")
            return False
    
    def generate_setup_files(self):
        """Generate all setup files and instructions."""
        print("🚀 Alpha Machine Slack Bot Configuration Generator")
        print("=" * 55)
        
        # Test service first
        if not self.test_service_endpoints():
            print("⚠️  Service endpoints not responding. Check deployment first.")
            return
        
        # Generate manifest file
        manifest = self.create_app_manifest()
        
        print("\n📝 Generating configuration files...")
        
        # Save manifest
        with open('slack_app_manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        print("   ✅ Created: slack_app_manifest.json")
        
        # Save setup instructions
        setup_instructions = self.generate_manual_setup_commands()
        with open('slack_setup_instructions.md', 'w') as f:
            f.write(setup_instructions)
        print("   ✅ Created: slack_setup_instructions.md")
        
        # Save curl commands
        curl_commands = self.create_curl_commands()
        with open('slack_api_commands.sh', 'w') as f:
            f.write(curl_commands)
        print("   ✅ Created: slack_api_commands.sh")
        
        print(f"\n🎯 Next Steps:")
        print("=" * 20)
        print("1. Go to: https://api.slack.com/apps?new_app=1")
        print("2. Select 'From an app manifest'")
        print("3. Paste contents of: slack_app_manifest.json")
        print("4. Follow instructions in: slack_setup_instructions.md")
        print("5. Test with: python test_slack_integration.py")
        
        print(f"\n📋 Your service URL: {self.service_url}")
        print("🔗 Slack App Creation: https://api.slack.com/apps?new_app=1")


def main():
    """Main configuration function."""
    configurator = SlackAppConfigurator()
    configurator.generate_setup_files()


if __name__ == "__main__":
    main() 