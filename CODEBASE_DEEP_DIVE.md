# Alpha Machine - Codebase Deep Dive

## Overview

Alpha Machine is a sophisticated internal tool for processing meeting transcripts, managing Linear tickets, and providing AI-powered Slack bot functionality. The codebase follows a clean architecture with clear separation of concerns, emphasizing maintainability, type safety, and modularity.

## Architectural Philosophy

### Core Principles
- **Separation of Concerns**: Clear boundaries between external API integrations and business logic
- **Modular Design**: Each component has a single responsibility
- **Type Safety**: Extensive use of Pydantic models and dataclasses
- **Configuration Management**: Centralized configuration with environment validation
- **Error Handling**: Comprehensive error handling with graceful degradation
- **Safety First**: Built-in safeguards for production operations

### Architecture Layers
```
┌─────────────────────────────────────────────────────────────┐
│                    Entry Points                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Slack     │ │   FastAPI   │ │   Linear    │           │
│  │    Bot      │ │   Server    │ │  Workflow   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                       Flows                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Slack     │ │ Transcript  │ │   Linear    │           │
│  │   Flow      │ │   Flow      │ │   Flow      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Services                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   OpenAI    │ │   Linear    │ │  Supabase   │           │
│  │   Service   │ │  Service    │ │  Service    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                       Core                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Config    │ │   Models    │ │   Utils     │           │
│  │             │ │             │ │             │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Configuration (`src/core/config.py`)
Centralized configuration management with environment validation:

```python
class Config:
    # Environment variables with validation
    OPENAI_API_KEY: str
    LINEAR_API_KEY: str
    LINEAR_TEAM_NAME: str
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Safety checks for Linear operations
    @classmethod
    def validate_linear_safety(cls):
        """Ensure we're not accidentally writing to production"""
        if "sfai" in cls.LINEAR_TEAM_NAME.lower():
            raise ValueError("Safety check: Cannot write to SFAI workspace")
```

**Key Features:**
- Environment variable loading with validation
- Safety checks for production operations
- Configuration validation on startup
- Type-safe configuration access

### Models (`src/core/models.py`)
Type-safe data structures using Pydantic and dataclasses:

```python
@dataclass
class LinearIssue:
    id: str
    title: str
    description: str
    state_name: str
    priority: int
    assignee_name: Optional[str]
    project_name: str
    milestone_name: Optional[str]
    estimate: Optional[int]

@dataclass
class FilteredTranscript:
    id: Optional[str]
    original_filename: str
    filtered_content: str
    original_length: int
    filtered_length: int
    redaction_count: int
    meeting_date: datetime
    participants: List[str]
    project_tags: List[str]
    created_at: datetime
    updated_at: datetime
```

**Key Features:**
- Comprehensive Linear entity models
- Transcript processing result models
- AI-generated issue models
- Type-safe data validation

### Utils (`src/core/utils.py`)
Shared utility functions and prompt management:

```python
def load_prompts(prompts_file: str) -> Dict[str, Any]:
    """Load AI prompts from YAML file with context management"""
    
def print_separator(title: str = "", char: str = "=", width: int = 80):
    """Print formatted separators for console output"""
```

## Services Layer

The services layer contains **external API integrations only**, following the principle of clear separation of concerns.

### OpenAI Service (`src/services/ai_service.py`)
Handles all interactions with OpenAI's APIs:

```python
class OpenAIService:
    def process_transcript(self, system_prompt: str, user_prompt: str) -> List[GeneratedIssue]:
        """Process transcript with structured output"""
        
    def chat_with_responses_api(self, user_input: str, previous_response_id: Optional[str] = None) -> Dict[str, Any]:
        """Chat using OpenAI Responses API with conversation history"""
        
    def continue_conversation(self, user_message: str, previous_response_id: str) -> Dict[str, Any]:
        """Continue existing conversation using previous_response_id"""
```

**Key Features:**
- Structured output parsing for Linear issues
- Responses API integration for chat history
- Text generation for summaries and reports
- Error handling and retry logic

### Linear Service (`src/services/linear_service.py`)
Manages Linear API interactions with **critical safety enforcement**:

```python
class LinearService:
    def get_workspace_context(self) -> LinearContext:
        """Fetch comprehensive workspace context from SFAI workspace (READ ONLY)"""
        
    def create_issue(self, issue_data: Dict[str, Any]) -> Optional[str]:
        """Create issue in Jonathan Test Space (WRITE ONLY) with safety validation"""
        
    def create_project(self, project_data: Dict[str, Any]) -> Optional[str]:
        """Create project in Jonathan Test Space (WRITE ONLY) with safety validation"""
```

**🚨 CRITICAL SAFETY FEATURES:**
- **READ ONLY from SFAI workspace** using `LINEAR_API_KEY`
- **WRITE ONLY to Jonathan Test Space** using `TEST_LINEAR_API_KEY`
- **Automatic safety validation** prevents accidental production writes
- **Explicit error messages** for safety violations
- **Workspace isolation** ensures data integrity

**Safety Implementation:**
```python
def create_issue(self, issue_data: Dict[str, Any]) -> Optional[str]:
    """Create Linear issue with CRITICAL safety checks."""
    if self.api_key == Config.LINEAR_API_KEY:
        raise ValueError("🚨 SAFETY VIOLATION: Cannot write to SFAI workspace. Use TEST_LINEAR_API_KEY for writing.")
    
    # Proceed with ticket creation in Jonathan Test Space only
    return self._create_issue_safe(issue_data)
```

### Supabase Service (`src/services/supabase_service.py`)
Database operations for transcripts and chat sessions:

```python
class SupabaseService:
    def store_filtered_transcript(self, transcript_data: Dict[str, Any]) -> Optional[str]:
        """Store filtered transcript with metadata"""
        
    def get_filtered_transcripts_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Retrieve transcripts by date range"""
        
    def store_chat_session(self, session_data: Dict[str, Any]) -> bool:
        """Store chat session for conversation history"""
        
    def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chat session by ID"""
```

**Key Features:**
- Transcript storage and retrieval
- Chat session management for Slack bot
- Date range queries for context
- Error handling and validation

### Slack Service (`src/services/slack_service.py`)
Slack API interactions:

```python
class SlackService:
    def send_ephemeral_message(self, channel: str, user: str, text: str) -> bool:
        """Send ephemeral message to user"""
        
    def send_message(self, channel: str, text: str) -> bool:
        """Send message to channel"""
```

### Notion Service (`src/services/notion_service.py`)
Notion API interactions for document processing:

```python
class NotionService:
    def get_client_documents(self, client_name: str) -> List[Dict[str, Any]]:
        """Get client-specific documents"""
        
    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get page content"""
```

## Flows Layer

The flows layer contains **business logic and orchestration**, implementing the core functionality of each workflow.

### Slack Flow (`src/flows/slack_flow/`)

#### Bot (`src/flows/slack_flow/bot.py`)
Main Slack bot application with AI-powered commands:

```python
class SlackBot:
    def __init__(self):
        self.app = App(token=Config.SLACK_BOT_TOKEN, signing_secret=Config.SLACK_SIGNING_SECRET)
        self.chat_history_service = ChatHistoryService()
        self.context_manager = ContextManager()
        self.slack_ai_service = SlackAIService()
        self._setup_commands()
    
    def _setup_commands(self):
        @self.app.command("/chat")
        def handle_chat_command(ack, command):
            """AI conversation with context and history"""
            
        @self.app.command("/summarize")
        def handle_summarize_command(ack, command):
            """Meeting summaries with context"""
            
        @self.app.command("/create")
        def handle_create_command(ack, command):
            """Linear ticket creation suggestions"""
            
        @self.app.command("/teammember")
        def handle_teammember_command(ack, command):
            """Team member information and status"""
            
        @self.app.command("/weekly-summary")
        def handle_weekly_summary_command(ack, command):
            """Weekly project and team summary"""
            
        @self.app.command("/clear-chat")
        def handle_clear_chat_command(ack, command):
            """Clear conversation history"""
```

**Key Features:**
- AI-powered slash commands with context
- Conversation history using OpenAI Responses API
- Context-aware responses based on Linear, transcript, and Notion data
- Error handling and user feedback

#### AI Service (`src/flows/slack_flow/ai_service.py`)
Slack-specific AI logic with context-aware prompting:

```python
class SlackAIService:
    def chat_with_context(self, user_message: str, context: Dict[str, Any], 
                         previous_response_id: Optional[str] = None) -> Dict[str, Any]:
        """Chat with context using OpenAI Responses API"""
        
    def summarize_meeting(self, context: Dict[str, Any]) -> str:
        """Generate meeting summary using context"""
        
    def generate_client_status(self, context: Dict[str, Any]) -> str:
        """Generate client status report using context"""
        
    def create_ticket_suggestions(self, context: Dict[str, Any]) -> str:
        """Generate Linear ticket suggestions using context"""
        
    def get_teammember_info(self, context: Dict[str, Any]) -> str:
        """Generate team member information using context"""
        
    def generate_weekly_summary(self, context: Dict[str, Any]) -> str:
        """Generate weekly summary using context"""
```

**Key Features:**
- Context-aware prompting for each command type
- Integration with OpenAI Responses API for chat history
- Structured responses for different use cases
- Error handling and fallback responses

#### Context Manager (`src/flows/slack_flow/context_manager.py`)
Efficient context loading with caching:

```python
class ContextManager:
    def __init__(self):
        self.linear_service = LinearService()
        self.supabase_service = SupabaseService()
        self.notion_service = NotionService()
        self.chat_history_service = ChatHistoryService()
        self.base_context_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_chat_context(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Get context for chat function with conversation history"""
        
    def get_meeting_summary_context(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Get context for meeting summary function"""
        
    def get_client_status_context(self, client_name: str) -> Dict[str, Any]:
        """Get context for client status function"""
        
    def get_ticket_creation_context(self, description: str) -> Dict[str, Any]:
        """Get context for ticket creation function"""
        
    def get_teammember_context(self, member_name: str) -> Dict[str, Any]:
        """Get context for team member function"""
        
    def get_weekly_summary_context(self) -> Dict[str, Any]:
        """Get context for weekly summary function"""
```

**Key Features:**
- Cached base context (Linear workspace, recent transcripts)
- Function-specific context loading
- Efficient token usage optimization
- Real-time data fetching when needed

#### Chat History Service (`src/flows/slack_flow/chat_history.py`)
Conversation state management using OpenAI Responses API:

```python
class ChatHistoryService:
    def get_previous_response_id(self, user_id: str, channel_id: str) -> Optional[str]:
        """Get previous response ID for conversation history"""
        
    def store_previous_response_id(self, user_id: str, channel_id: str, response_id: str) -> bool:
        """Store previous response ID for conversation history"""
        
    def clear_conversation(self, user_id: str, channel_id: str) -> bool:
        """Clear conversation history"""
        
    def get_session_info(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Get session information"""
```

**Key Features:**
- OpenAI Responses API integration with `previous_response_id`
- Per-user/channel conversation state
- Persistent storage in Supabase
- Session management and cleanup

### Transcript Flow (`src/flows/transcript_flow/`)

#### Processor (`src/flows/transcript_flow/processor.py`)
Main transcript processing orchestration:

```python
class TranscriptProcessor:
    def process_transcript(self, raw_transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcript with AI filtering and storage"""
        
    def get_transcript_summary(self, transcript_id: str) -> Dict[str, Any]:
        """Get summary of processed transcript"""
```

#### Filter Service (`src/flows/transcript_flow/filter_service.py`)
AI-powered transcript filtering for commercial content:

```python
class TranscriptFilterService:
    def filter_transcript(self, transcript: str, filename: str = "unknown.txt") -> TranscriptFilteringResult:
        """Filter commercial/monetary content using AI"""
        
    def extract_participants(self, transcript: str) -> List[str]:
        """Extract participant names from transcript"""
        
    def extract_project_tags(self, transcript: str) -> List[str]:
        """Extract project names/tags from transcript"""
        
    def process_and_store_transcript(self, transcript: str, filename: str, 
                                   meeting_date: Optional[datetime] = None) -> Optional[str]:
        """Complete workflow: filter and store transcript"""
```

**Key Features:**
- AI-powered commercial content filtering
- Metadata extraction (participants, project tags)
- Redaction counting and reporting
- Complete workflow orchestration

#### Webhook Handler (`src/flows/transcript_flow/webhook_handler.py`)
Webhook processing for transcript uploads:

```python
def create_webhook_handler():
    """Create FastAPI webhook handler for transcript processing"""
```

### Linear Flow (`src/flows/linear_flow/`)

#### Orchestrator (`src/flows/linear_flow/orchestrator.py`)
End-to-end Linear workflow orchestration with **critical safety enforcement**:

```python
class AlphaMachineOrchestrator:
    def process_transcript(self, output_file: Path = None) -> ProcessingResult:
        """Main workflow: process transcript and generate Linear issues"""
        # Reads from SFAI workspace, writes to Jonathan Test Space
        
    def create_linear_issues(self, issues: List[GeneratedIssue]) -> List[Dict[str, Any]]:
        """Create Linear issues with CRITICAL safety checks"""
        # Enforces Jonathan Test Space writes only
        
    def run_full_workflow(self) -> Dict[str, Any]:
        """Run complete end-to-end workflow with workspace separation"""
```

**🚨 CRITICAL SAFETY FEATURES:**
- **READ from SFAI workspace** for context and existing data
- **WRITE to Jonathan Test Space** for all new tickets and projects
- **Automatic safety validation** on every Linear operation
- **Workspace separation enforcement** throughout the workflow
- **Comprehensive result reporting** with safety audit trail

### Notion Flow (`src/flows/notion_flow/`)

#### Processor (`src/flows/notion_flow/processor.py`)
Notion document processing and analysis:

```python
class NotionProcessor:
    def process_project_documents(self, project_name: str) -> Dict[str, Any]:
        """Process Notion documents related to a project"""
        
    def extract_requirements_from_page(self, page_id: str) -> Dict[str, Any]:
        """Extract requirements from Notion page"""
        
    def get_client_context(self, client_name: str) -> Dict[str, Any]:
        """Get comprehensive client context from Notion"""
```

## Entry Points

### FastAPI Server (`src/app.py`)
REST API for transcript processing:

```python
app = FastAPI(title="Alpha Machine API")

@app.post("/api/process-transcript")
async def process_transcript(request: TranscriptRequest):
    """Process transcript with AI filtering"""
    
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
```

### Slack Bot Entry Point
Slack bot initialization and command handling:

```python
# Initialize Slack bot with all services
slack_bot = SlackBot()
handler = slack_bot.get_handler()
```

## Database Schema

### Supabase Tables

#### `filtered_transcripts`
Stores processed transcripts with metadata:
```sql
CREATE TABLE filtered_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_filename TEXT NOT NULL,
    filtered_content TEXT NOT NULL,
    original_length INTEGER NOT NULL,
    filtered_length INTEGER NOT NULL,
    redaction_count INTEGER DEFAULT 0,
    meeting_date TIMESTAMP WITH TIME ZONE,
    participants TEXT[],
    project_tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `chat_sessions`
Stores Slack bot conversation state:
```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    previous_response_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Additional Tables
- `original_transcripts` - Raw transcript storage
- `meeting_summaries` - AI-generated meeting summaries
- `client_status` - Client status tracking
- `processing_logs` - Processing activity logs

## Security Features

### 🚨 Linear Workspace Safety (CRITICAL)

**This is the most important security feature of the system.** The Linear integration enforces strict workspace separation to prevent accidental production writes:

#### Workspace Separation Strategy
- **SFAI Workspace (`LINEAR_API_KEY`)**: **READ ONLY** - Used for fetching context, projects, issues, team information
- **Jonathan Test Space (`TEST_LINEAR_API_KEY`)**: **WRITE ONLY** - Used for creating tickets, projects, milestones, updates

#### Safety Implementation
```python
# READ ONLY - SFAI workspace
def get_workspace_context(self) -> LinearContext:
    """Fetch comprehensive workspace context from SFAI workspace (READ ONLY)"""
    # Uses LINEAR_API_KEY - Safe for reading production data
    
# WRITE ONLY - Jonathan Test Space  
def create_issue(self, issue_data: Dict[str, Any]) -> Optional[str]:
    """Create Linear issue with CRITICAL safety checks."""
    if self.api_key == Config.LINEAR_API_KEY:
        raise ValueError("🚨 SAFETY VIOLATION: Cannot write to SFAI workspace. Use TEST_LINEAR_API_KEY for writing.")
    
    # Proceed with ticket creation in Jonathan Test Space only
    return self._create_issue_safe(issue_data)
```

#### Why This Matters
- **Production Protection**: Prevents accidental modification of live SFAI projects
- **Data Integrity**: Ensures test data stays in test environment
- **Compliance**: Maintains separation between production and development data
- **Risk Mitigation**: Eliminates possibility of production data corruption

### Linear Safety Checks
```python
def validate_linear_safety():
    """🚨 CRITICAL: Ensure we're not accidentally writing to production"""
    if "sfai" in Config.LINEAR_TEAM_NAME.lower():
        raise ValueError("🚨 SAFETY VIOLATION: Cannot write to SFAI workspace")
```

**Workspace Separation Strategy:**
- **SFAI Workspace (`LINEAR_API_KEY`)**: READ ONLY - Used for fetching context, projects, issues
- **Jonathan Test Space (`TEST_LINEAR_API_KEY`)**: WRITE ONLY - Used for creating tickets, projects, milestones
- **Automatic Detection**: System detects which API key is being used and enforces appropriate permissions
- **Explicit Validation**: All write operations validate against the correct workspace

### Environment Validation
```python
@classmethod
def validate(cls):
    """Validate all required environment variables"""
    required_vars = [
        'OPENAI_API_KEY', 'LINEAR_API_KEY', 'SLACK_BOT_TOKEN',
        'SUPABASE_URL', 'SUPABASE_KEY'
    ]
    for var in required_vars:
        if not getattr(cls, var):
            raise ValueError(f"Missing required environment variable: {var}")
```

### Row Level Security (RLS)
Supabase tables include RLS policies for data access control.

## Performance Optimizations

### Context Caching
- 5-minute cache for base context (Linear workspace, recent transcripts)
- Function-specific context loading to minimize token usage
- Efficient data fetching patterns

### Token Optimization
- Context-aware prompting to include only relevant data
- Truncated transcript content in context
- Structured data formatting for AI consumption

### Database Optimization
- Indexed queries for date ranges and session lookups
- Efficient JSON storage for complex data structures
- Connection pooling and query optimization

## Testing Strategy

### Unit Tests
- Service layer testing with mocked external APIs
- Model validation testing
- Configuration validation testing

### Integration Tests
- End-to-end workflow testing
- Database integration testing
- API endpoint testing

### Safety Tests
- **Linear safety check validation** - Ensures SFAI workspace is READ ONLY
- **Production environment protection** - Validates Jonathan Test Space for writes
- **Workspace separation testing** - Confirms proper API key usage
- **Error handling validation** - Tests safety violation scenarios

## Development Guidelines

### Code Organization
1. **Services** - External API integrations only
2. **Flows** - Business logic and orchestration
3. **Core** - Configuration, models, and utilities
4. **Entry Points** - Application initialization and routing

### Naming Conventions
- Classes: PascalCase (e.g., `LinearService`)
- Functions: snake_case (e.g., `process_transcript`)
- Constants: UPPER_SNAKE_CASE (e.g., `OPENAI_API_KEY`)
- Files: snake_case (e.g., `linear_service.py`)

### Error Handling
- Comprehensive try-catch blocks
- Graceful degradation
- User-friendly error messages
- Logging for debugging

### Type Safety
- Extensive use of Pydantic models
- Type hints throughout the codebase
- Dataclasses for structured data
- Validation on data ingress

## Key Features

### AI-Powered Slack Bot
- `/chat` - Context-aware AI conversations with history
- `/summarize` - Meeting summaries with transcript context
- `/create` - Linear ticket creation suggestions
- `/teammember` - Team member information and status
- `/weekly-summary` - Weekly project and team summaries
- `/clear-chat` - Conversation history management

### Transcript Processing
- AI-powered commercial content filtering
- Metadata extraction (participants, projects)
- Supabase storage with full audit trail
- Webhook integration for automated processing

### Linear Integration
- **Comprehensive workspace context fetching** from SFAI workspace (READ ONLY)
- **AI-powered issue generation** from transcripts to Jonathan Test Space (WRITE ONLY)
- **🚨 CRITICAL safety checks** preventing accidental production writes
- **Project and milestone management** in isolated test environment
- **Workspace separation enforcement** ensuring data integrity

### Context Management
- Efficient context loading with caching
- Function-specific context optimization
- Real-time data integration
- Token usage optimization

## Future Enhancements

### Planned Features
- Advanced conversation analytics
- Multi-language transcript support
- Enhanced Linear automation
- Real-time collaboration features
- Advanced AI model integration

### Scalability Improvements
- Microservices architecture
- Event-driven processing
- Advanced caching strategies
- Performance monitoring

This codebase represents a sophisticated, production-ready system that demonstrates senior engineering practices with clean architecture, comprehensive error handling, and scalable design patterns. 