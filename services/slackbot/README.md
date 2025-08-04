# Alpha Machine - Slackbot Service

## Overview

The Slackbot service provides comprehensive AI-powered Slack commands that integrate deeply with Linear workspace data, meeting transcripts, and project management workflows. It serves as the primary interface for team members to interact with project data and AI assistance.

## Features

### Advanced Linear Integration
- **Real-time Linear Context**: Accesses current workspace state, projects, milestones, and issues
- **AI-Powered Ticket Management**: Create and update Linear tickets with intelligent analysis
- **Team Coordination**: Track team member assignments, progress, and workloads
- **Project Status**: Get comprehensive project and client status updates

### AI-Powered Commands

#### `/chat [question]`
AI conversation with full Linear workspace context and meeting history.

**Usage:**
```
/chat What are our current project priorities?
/chat Who is working on the authentication feature?
/chat What was decided about the client deadline in recent meetings?
```

**Features:**
- Accesses filtered transcript data from recent meetings
- Includes current Linear workspace state (projects, issues, progress)
- Provides contextual responses based on available information
- Maintains conversation context with Slack history

#### `/summarize`
Generate comprehensive summaries for meetings and client status.

**Meeting Summaries:**
```
/summarize last @meeting @14:30
/summarize last @standup @morning
```

**Client Status:**
```
/summarize client acme_corp
/summarize client [client_name]
```

**Features:**
- AI-generated meeting summaries with key decisions and action items
- Client status with deadlines, progress, and team assignments
- Integration with Linear projects and Notion documents
- Professional format suitable for stakeholder communication

#### `/create` or `/create-ticket [description]`
AI-powered Linear ticket creation with intelligent analysis.

**Usage:**
```
/create Implement user authentication system
/create Fix the bug in the payment processing module
/create Setup CI/CD pipeline for the new microservice
```

**Features:**
- **Test Mode Disabled**: Provides AI analysis of what ticket should be created
- **Test Mode Enabled**: Actually creates tickets in Linear workspace
- Suggests appropriate priority, time estimates, and assignments
- Maps requests to existing projects and milestones
- Provides context-aware ticket descriptions

#### `/update [ticket_description]`
Update existing Linear tickets with intelligent parsing.

**Usage:**
```
/update ticket ABC-123 to in progress
/update ABC-123: change title to 'New Task Name'
/update mark ticket XYZ-456 as completed
/update assign ticket DEF-789 to john@company.com
/update set priority of ticket GHI-101 to high
```

**Features:**
- **Test Mode Disabled**: Provides AI analysis of what would be updated
- **Test Mode Enabled**: Actually updates tickets in Linear workspace
- Supports title, description, status, assignee, priority, and deadline changes
- Intelligent parsing of natural language update requests
- Returns updated ticket information and links

#### `/teammember [username]`
Comprehensive team member information and project assignments.

**Usage:**
```
/teammember @john_doe
/teammember john@company.com
/teammember John Doe
```

**Features:**
- Active issues and project assignments
- Recent completed work and performance
- Current workload and availability
- Integration with Slack user info and Linear work data

#### `/weekly-summary`
Automatic weekly summary generation for stakeholders.

**Usage:**
```
/weekly-summary
```

**Features:**
- Combines meeting data, project progress, and team performance
- Professional format suitable for client communication
- Highlights key accomplishments and upcoming milestones
- Strategic insights and recommendations

## Architecture

### Safety Features
- **Production Safety**: All write operations require `LINEAR_TEST_MODE=true`
- **Read-Only Default**: Commands provide analysis without modifying data
- **Error Handling**: Comprehensive error handling and user feedback

### AI Integration
- **Structured Prompts**: Uses `prompts.yml` for consistent AI behavior
- **Context Awareness**: Combines Linear data, meeting transcripts, and Slack history
- **Intelligent Parsing**: Natural language processing for commands

### Linear Integration
- **Real-Time Data**: Fetches current workspace state for every command
- **GraphQL API**: Efficient queries for projects, issues, and team data
- **Comprehensive Context**: Includes projects, milestones, issues, and team members

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack bot user OAuth token |
| `SLACK_SIGNING_SECRET` | Yes | Slack app signing secret |
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI features |
| `LINEAR_API_KEY` | Yes | Linear API key for workspace access |
| `LINEAR_TEAM_NAME` | No | Team name (default: "SFAI Labs") |
| `LINEAR_DEFAULT_ASSIGNEE` | No | Default assignee email |
| `LINEAR_TEST_MODE` | No | Enable write operations (default: false) |
| `SUPABASE_URL` | Yes | Supabase URL for transcript data |
| `SUPABASE_KEY` | Yes | Supabase service role key |
| `NOTION_TOKEN` | No | Notion API token (optional) |

### Test Mode Safety
To enable actual Linear ticket creation and updates, set:
```bash
export LINEAR_TEST_MODE=true
```

**Warning**: Only enable test mode in development environments or when you intend to modify your Linear workspace.

## Development

### Running the Service
```bash
# Start the slackbot service
uv run python services/slackbot/main.py

# Or using make
make run service=slackbot
```

### Testing
```bash
# Run comprehensive integration tests
uv run python tests/test_slackbot_linear_integration.py

# Run local testing without Slack
uv run python services/slackbot/test_slackbot_local.py
```

### Adding New Commands
1. Add command handler method in `command_handler.py`
2. Add routing in `handle_command()` method
3. Add prompts to `shared/core/prompts.yml`
4. Add tests in `tests/test_slackbot_linear_integration.py`

## API Endpoints

The service runs on port 8001 with these endpoints:

- `POST /commands/slack` - Slack slash command webhooks
- `POST /events/slack` - Slack event subscriptions
- `POST /webhooks/*` - Various webhook handlers
- `GET /` - Service health check

## Slack App Configuration

### Slash Commands
Configure these commands in your Slack app:

| Command | Request URL | Description |
|---------|-------------|-------------|
| `/chat` | `https://your-domain/commands/slack` | AI conversation |
| `/summarize` | `https://your-domain/commands/slack` | Meeting/client summaries |
| `/create` | `https://your-domain/commands/slack` | Create Linear tickets |
| `/update` | `https://your-domain/commands/slack` | Update Linear tickets |
| `/teammember` | `https://your-domain/commands/slack` | Team member info |
| `/weekly-summary` | `https://your-domain/commands/slack` | Weekly reports |

### Permissions
Required OAuth scopes:
- `commands` - Slash commands
- `chat:write` - Send messages
- `users:read` - Read user information
- `channels:history` - Read channel messages (for context)

## Troubleshooting

### Common Issues

**"Slack bot token not configured"**
- Set `SLACK_BOT_TOKEN` environment variable
- Verify token starts with `xoxb-`

**"Linear API request failed"**
- Verify `LINEAR_API_KEY` is valid
- Check Linear team name matches your workspace

**"Test Mode Disabled" messages**
- Set `LINEAR_TEST_MODE=true` to enable write operations
- This is a safety feature to prevent accidental production changes

**AI responses are generic**
- Verify OpenAI API key is valid and has credits
- Check prompts.yml file exists and is readable

### Debug Mode
Add verbose logging by setting:
```bash
export DEBUG=true
```

## Security

- All Linear write operations require explicit test mode enablement
- Sensitive transcript data is automatically filtered
- API tokens are never logged or exposed
- All AI interactions are logged for audit purposes
