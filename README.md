# Alpha Machine

AI-powered transcript processing and Linear ticket generation tool.

## Overview

Alpha Machine is a sophisticated internal tool that processes meeting transcripts using AI and automatically generates structured Linear tickets. It's designed for heavy internal use with a focus on maintainability, readability, and extensibility.

## Project Structure

```
alpha-machine/
├── src/                          # Main source code
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration management
│   ├── models.py                # Data models and structures
│   ├── orchestrator.py          # Main workflow orchestrator
│   ├── utils.py                 # Utility functions
│   ├── prompts.yml              # AI prompts configuration
│   └── services/                # Service layer
│       ├── __init__.py          # Services package
│       ├── linear_service.py    # Linear API interactions
│       ├── openai_service.py    # OpenAI API interactions
│       └── transcript_service.py # Transcript processing
├── main.py                      # Application entry point
├── config.py                    # Legacy config (deprecated)
├── process_transcript.py        # Legacy script (deprecated)
├── pyproject.toml              # Project configuration
├── uv.lock                     # Dependency lock file
└── README.md                   # This file
```

## Architecture

### Core Components

1. **Orchestrator** (`src/orchestrator.py`)
   - Main coordinator for the entire workflow
   - Manages service initialization and workflow execution
   - Handles error handling and result aggregation

2. **Services** (`src/services/`)
   - **LinearService**: Handles all Linear API interactions
   - **OpenAIService**: Manages OpenAI API calls and response parsing
   - **TranscriptService**: Handles transcript loading and prompt formatting

3. **Models** (`src/models.py`)
   - Structured data classes for all entities
   - Type-safe data handling throughout the application
   - Clear separation between API responses and internal representations

4. **Configuration** (`src/config.py`)
   - Centralized configuration management
   - Environment variable handling
   - Path management and validation

### Key Features

- **Separation of Concerns**: Each service has a single responsibility
- **Type Safety**: Full type hints throughout the codebase
- **Error Handling**: Comprehensive error handling at all levels
- **Extensibility**: Easy to add new services or modify existing ones
- **Maintainability**: Clear structure and documentation

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
   
   # Optional (for Linear integration)
   export LINEAR_API_KEY="your-linear-api-key"
   export TEST_LINEAR_API_KEY="your-test-linear-api-key"
   export LINEAR_TEAM_NAME="Your Team Name"
   export LINEAR_DEFAULT_ASSIGNEE="user@example.com"
   ```

### Running the Application

```bash
# Run the full workflow
uv run main.py

# Or run directly with Python
python main.py
```

### Configuration Options

The application supports various configuration options via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `OPENAI_MAX_TOKENS` | `4000` | Maximum tokens for API calls |
| `OPENAI_TEMPERATURE` | `0.1` | Temperature for AI responses |
| `LINEAR_API_KEY` | Optional | Linear API key for main workspace |
| `TEST_LINEAR_API_KEY` | Optional | Linear API key for test workspace |
| `LINEAR_TEAM_NAME` | `Jonathan Test Space` | Default team name |
| `LINEAR_DEFAULT_ASSIGNEE` | `jonny34923@gmail.com` | Default assignee email |

## Development

### Adding New Services

1. Create a new service class in `src/services/`
2. Follow the existing pattern with clear separation of concerns
3. Add the service to the orchestrator if needed
4. Update the services `__init__.py` file

### Adding New Models

1. Create new dataclasses in `src/models.py`
2. Use type hints and provide clear documentation
3. Include serialization methods if needed

### Testing

The project includes test files for various components:
- `test_linear_full_workflow.py`: End-to-end workflow testing
- `test_linear_write.py`: Linear API testing

## Migration from Legacy Code

The original `process_transcript.py` script has been refactored into a modular architecture:

- **Linear API functions** → `LinearService` class
- **OpenAI functions** → `OpenAIService` class  
- **File loading functions** → `TranscriptService` class
- **Main workflow** → `AlphaMachineOrchestrator` class

All functionality has been preserved while improving maintainability and extensibility.

## Deployment

The modular structure makes deployment straightforward:

1. **Docker**: Easy to containerize with clear service boundaries
2. **Cloud Functions**: Services can be deployed independently
3. **Microservices**: Each service can be deployed separately if needed

## Contributing

When contributing to this project:

1. Follow the existing code structure and patterns
2. Add type hints to all new functions
3. Include comprehensive error handling
4. Update documentation for any new features
5. Add tests for new functionality

## License

Internal tool - not for external distribution.
