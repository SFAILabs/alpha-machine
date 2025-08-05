
# Alpha Machine Bot - Manual Slack App Setup Instructions
# =====================================================

## 1. Create Slack App Using Manifest (Recommended)

Go to: https://api.slack.com/apps?new_app=1

Select "From an app manifest" and paste this JSON:

```json
{
  "display_information": {
    "name": "Alpha Machine Bot",
    "description": "AI-powered assistant for project management, meeting summaries, and team collaboration",
    "background_color": "#2c3e50",
    "long_description": "Alpha Machine Bot integrates with Linear, Supabase, and OpenAI to provide intelligent assistance for your team. Get meeting summaries, create and update tickets, track team member work, and chat with an AI that understands your project context."
  },
  "features": {
    "app_home": {
      "home_tab_enabled": true,
      "messages_tab_enabled": true
    },
    "bot_user": {
      "display_name": "Alpha Machine",
      "always_online": true
    },
    "slash_commands": [
      {
        "command": "/chat",
        "url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands",
        "description": "Chat with AI assistant about projects and work",
        "usage_hint": "What are our current project priorities?",
        "should_escape": false
      },
      {
        "command": "/summarize",
        "url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands",
        "description": "Get meeting summaries or client status updates",
        "usage_hint": "last meeting | client [client_name]",
        "should_escape": false
      },
      {
        "command": "/create",
        "url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands",
        "description": "Create Linear tickets with AI assistance",
        "usage_hint": "Fix login bug with better error handling",
        "should_escape": false
      },
      {
        "command": "/update",
        "url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands",
        "description": "Update existing Linear tickets",
        "usage_hint": "ABC-123 to in progress",
        "should_escape": false
      },
      {
        "command": "/teammember",
        "url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands",
        "description": "Get team member information and current work",
        "usage_hint": "john@company.com",
        "should_escape": false
      },
      {
        "command": "/weekly-summary",
        "url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands",
        "description": "Generate comprehensive weekly team report",
        "usage_hint": "(no parameters needed)",
        "should_escape": false
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
      "request_url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/events",
      "bot_events": [
        "app_mention",
        "message.im",
        "reaction_added",
        "team_join"
      ]
    },
    "interactivity": {
      "is_enabled": true,
      "request_url": "https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/interactive"
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": false,
    "token_rotation_enabled": false
  }
}
```

## 2. Alternative: Manual Configuration Steps

If you prefer manual setup, go to https://api.slack.com/apps and:

### A. Create New App
- Name: "Alpha Machine Bot"
- Choose your workspace

### B. Configure Slash Commands
Add these commands (Features → Slash Commands):


Command: /chat
Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands
Description: Chat with AI assistant about projects and work
Usage Hint: What are our current project priorities?

Command: /summarize
Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands
Description: Get meeting summaries or client status updates
Usage Hint: last meeting | client [client_name]

Command: /create
Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands
Description: Create Linear tickets with AI assistance
Usage Hint: Fix login bug with better error handling

Command: /update
Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands
Description: Update existing Linear tickets
Usage Hint: ABC-123 to in progress

Command: /teammember
Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands
Description: Get team member information and current work
Usage Hint: john@company.com

Command: /weekly-summary
Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/commands
Description: Generate comprehensive weekly team report
Usage Hint: (no parameters needed)


### C. Configure Event Subscriptions
(Features → Event Subscriptions)

Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/events

Bot Events to Subscribe To:
- app_mention
- message.im
- reaction_added
- team_join


### D. Configure Interactive Components
(Features → Interactivity & Shortcuts)

Request URL: https://slackbot-service-zyt7rmwq2a-uc.a.run.app/slack/interactive

### E. Set OAuth Scopes
(Features → OAuth & Permissions → Scopes)

Bot Token Scopes:
- app_mentions:read
- channels:history
- channels:read
- chat:write
- commands
- groups:history
- groups:read
- im:history
- im:read
- im:write
- mpim:history
- mpim:read
- reactions:read
- users:read
- users:read.email
- team:read


### F. Install App
(Settings → Install App)
- Click "Install to Workspace"
- Copy the Bot User OAuth Token (starts with xoxb-)
- Copy the Signing Secret from Basic Information

## 3. Update Environment Variables

After installation, update your Cloud Run service:

```bash
# Update with your actual tokens
gcloud run services update slackbot-service \
  --region=us-central1 \
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
