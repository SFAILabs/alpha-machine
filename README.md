# Alpha Machine

AI-powered transcript processing and project management system with advanced Slack bot integration.

## Overview

Alpha Machine is a sophisticated internal tool that processes meeting transcripts using AI, manages Linear tickets, and provides an intelligent Slack bot interface. It's designed for heavy internal use with a focus on maintainability, readability, and extensibility.

## Architecture

The project follows senior engineer practices with clear separation of concerns:

```
alpha-machine/
├── src/                          # Main source code
│   ├── core/                     # Core components
│   │   ├── __init__.py          # Core package exports
│   │   ├── config.py            # Configuration management
│   │   ├── models.py            # Data models and structures
│   │   ├── utils.py             # Utility functions
│   │   └── prompts.yml          # AI prompts configuration
│   ├── services/                # Service layer
│   │   ├── __init__.py          # Services package exports
│   │   ├── ai_service.py        # OpenAI API interactions
│   │   ├── supabase_service.py  # Supabase database operations
│   │   ├── linear_service.py    # Linear API interactions
│   │   ├── slack_service.py     # Slack API interactions
│   │   ├── notion_service.py    # Notion API interactions
│   │   └── transcript_service.py # Transcript processing utilities
│   ├── flows/                   # Business logic flows
│   │   ├── __init__.py          # Flows package exports
│   │   ├── transcript_flow/     # Transcript processing flow
│   │   │   ├── __init__.py
│   │   │   ├── processor.py     # AI filtering and storage
│   │   │   └── webhook_handler.py # Webhook endpoint
│   │   ├── slack_flow/          # Slack bot flow
│   │   │   ├── __init__.py
│   │   │   └── bot.py           # Advanced Slack bot with AI commands
│   │   ├── linear_flow/         # Linear ticket management
│   │   │   ├── __init__.py
│   │   │   └── orchestrator.py  # Main workflow orchestrator
│   │   └── notion_flow/         # Notion integration
│   │       ├── __init__.py
│   │       └── processor.py     # Notion document processing
│   └── __init__.py              # Main package exports
├── main.py                      # Linear workflow entry point
├── slack_bot.py                 # Slack bot entry point
├── webhook_server.py            # Transcript webhook server
├── pyproject.toml              # Project configuration
├── uv.lock                     # Dependency lock file
└── README.md                   # This file
```

## Core Components

### 1. Core Package (`src/core/`)
- **Config**: Centralized configuration management with environment variable handling
- **Models**: Type-safe data models using Pydantic and dataclasses
- **Utils**: Shared utility functions and prompt loading
- **Prompts**: YAML-based AI prompt configuration

### 2. Services Package (`src/services/`)
- **OpenAIService**: OpenAI API integration with structured output
- **SupabaseService**: Database operations for transcripts and metadata
- **LinearService**: Linear API integration for project management
- **SlackService**: Slack API integration for messaging and user info
- **NotionService**: Notion API integration for document management
- **TranscriptService**: Transcript loading and prompt formatting

### 3. Flows Package (`src/flows/`)
- **TranscriptFlow**: AI-powered transcript filtering and storage
- **SlackFlow**: Advanced Slack bot with comprehensive AI commands
- **LinearFlow**: Linear ticket generation and management
- **NotionFlow**: Notion document processing and requirements extraction

## Key Features

### Transcript Processing
- **AI Filtering**: Automatically filters commercial/monetary information from transcripts
- **Supabase Storage**: Stores filtered transcripts with timestamps and metadata
- **Webhook Integration**: Receives transcripts from Krisp via Zapier
- **Context Preservation**: Maintains meeting context for AI analysis

### Advanced Slack Bot
The Slack bot provides comprehensive AI-powered commands:

#### `/chat [question]`
- AI conversation with full context from recent meetings and Linear workspace
- Accesses filtered transcript data and current project status
- Provides contextual responses based on available information

#### `/summarize last @meeting @timestamp`
- Generates meeting summaries with key decisions, action items, and deadlines
- Supports timestamp-based meeting selection
- Extracts commercial/monetary information discussed

#### `/summarize client [client_name]`
- Comprehensive client status summary with deadlines and progress
- Integrates Linear projects, Notion documents, and client metadata
- Shows project timelines and team assignments

#### `/create [description]`
- AI-powered Linear ticket creation with context analysis
- Suggests appropriate tickets based on meeting context and user input
- Provides priority, time estimates, and assignment recommendations

#### `/teammember @username`
- Team member information with active issues and project assignments
- Shows recent completed work and current status
- Integrates Slack user info with Linear work data

#### `/weekly-summary`
- Automatic weekly summary generation for stakeholders
- Combines meeting data, project progress, and team performance
- Professional format suitable for client communication

### Linear Integration
- **Workspace Context**: Real-time Linear workspace state analysis
- **Ticket Generation**: AI-powered ticket creation from meeting context
- **Project Management**: Comprehensive project and milestone tracking
- **Team Coordination**: Issue assignment and progress monitoring

### Notion Integration
- **Document Processing**: Extracts requirements and specifications from Notion pages
- **Client Context**: Retrieves client documents and project information
- **Requirements Analysis**: AI-powered analysis of Notion content for Linear tickets

## Development Workflow

This project is managed by a central `Makefile` that uses `uv` to handle a shared virtual environment.

### 1. Install All Dependencies
This one-time command will create a single, shared virtual environment (`.venv`) and install all project dependencies, including all local services as editable packages.
```bash
make install
```

### 2. Run Services for Development
To run all services (transcript, linear, notion, slackbot) in the background, use:
```bash
make run-dev
```
Logs for each service will be redirected to `/tmp/alpha-machine-<service_name>.log`.

To run a single service in the foreground for debugging:
```bash
make run service=transcript
```

### 3. Run the Transcript to Linear Test
With the services running, you can execute the end-to-end test for the transcript and linear services:
```bash
make test-transcript-linear
```

### 4. Stop All Services
This command will find and stop all the background services started with `run-dev`.
```bash
make stop
```

## Usage

### Prerequisites

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set up environment variables:
   ```bash
   # Required
   export OPENAI_API_KEY="your-openai-api-key"
   export SUPABASE_URL="your-supabase-url"
   export SUPABASE_KEY="your-supabase-key"
   
   # Slack Bot
   export SLACK_BOT_TOKEN="your-slack-bot-token"
   export SLACK_SIGNING_SECRET="your-slack-signing-secret"
   
   # Linear (Optional)
   export LINEAR_API_KEY="your-linear-api-key"
   export LINEAR_TEAM_NAME="Your Team Name"
   export LINEAR_TEST_MODE=false
   
   # Notion (Optional)
   export NOTION_TOKEN="your-notion-token"
   ```

### Running the Application

#### 1. Linear Workflow (Legacy)
```bash
# Run the full Linear workflow
uv run main.py
```

#### 2. Slack Bot
```bash
# Start the Slack bot server
uv run slack_bot.py
```

#### 3. Transcript Webhook Server
```bash
# Start the webhook server for transcript processing
uv run webhook_server.py
```

### Slack Bot Commands

Once the Slack bot is running, you can use these commands in any Slack channel:

```bash
# AI conversation with context
/chat What was discussed about the client project in recent meetings?

# Meeting summary
/summarize last @meeting @14:30

# Client status
/summarize client acme_corp

# Create tickets
/create tickets for the new feature requirements

# Team member info
/teammember @john_doe

# Weekly summary
/weekly-summary
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `OPENAI_MAX_TOKENS` | `4000` | Maximum tokens for API calls |
| `OPENAI_TEMPERATURE` | `0.1` | Temperature for AI responses |
| `SUPABASE_URL` | Required | Supabase project URL |
| `SUPABASE_KEY` | Required | Supabase service role key |
| `SLACK_BOT_TOKEN` | Required | Slack bot user OAuth token |
| `SLACK_SIGNING_SECRET` | Required | Slack app signing secret |
| `LINEAR_API_KEY` | Optional | Linear API key |
| `LINEAR_TEAM_NAME` | `SFAI Labs` | Default team name |
| `LINEAR_TEST_MODE` | `false` | Enable test mode for writing to Linear |
| `NOTION_TOKEN` | Optional | Notion integration token |

## Development

### Adding New Services

1. Create a new service class in `src/services/`
2. Follow the existing pattern with clear separation of concerns
3. Add the service to `src/services/__init__.py`
4. Update the main `src/__init__.py` file

### Adding New Flows

1. Create a new flow directory in `src/flows/`
2. Implement the flow logic with proper error handling
3. Add the flow to `src/flows/__init__.py`
4. Update the main `src/__init__.py` file

### Adding New Models

1. Create new dataclasses in `src/core/models.py`
2. Use type hints and provide clear documentation
3. Include serialization methods if needed

### Testing

The project includes test files for various components:
- `test_linear_full_workflow.py`: End-to-end workflow testing
- `structured_project_view.py`: Project structure analysis

## Database Schema

### Supabase Tables

#### `transcripts`
- `id`: Primary key
- `raw_transcript`: Full meeting transcript
- `filtered_data`: AI-filtered commercial/monetary data
- `metadata`: Meeting metadata (date, participants, etc.)
- `created_at`: Timestamp
- `processed`: Boolean flag

#### `meeting_summaries`
- `id`: Primary key
- `transcript_id`: Reference to transcript
- `summary`: AI-generated summary
- `key_points`: Extracted key points
- `action_items`: Identified action items
- `created_at`: Timestamp

#### `client_status`
- `id`: Primary key
- `client_name`: Client identifier
- `status`: Current project status
- `deadline`: Project deadline
- `progress`: Progress percentage
- `updated_at`: Last update timestamp

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --frozen

EXPOSE 3000 5000

CMD ["uv", "run", "slack_bot.py"]
```

### Environment Setup
1. Set all required environment variables
2. Configure Slack app with slash commands
3. Set up Supabase database with required tables
4. Configure Linear and Notion integrations

## Contributing

When contributing to this project:

1. Follow the existing code structure and patterns
2. Add type hints to all new functions
3. Include comprehensive error handling
4. Update documentation for any new features
5. Add tests for new functionality
6. Use the established service/flow architecture

## License

Internal tool - not for external distribution.
