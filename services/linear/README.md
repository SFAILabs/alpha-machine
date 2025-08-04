# Alpha Machine - Linear Service

## Overview

The Linear service is responsible for all interactions with the Linear API, providing comprehensive workspace management, ticket creation, and project orchestration capabilities. It serves as the foundation for the Slackbot integration and AI-powered project management features.

## Features

### Workspace Management
- **Real-time Context**: Fetches current workspace state including projects, milestones, and issues
- **Team Coordination**: Manages team members, assignments, and workload distribution
- **Project Tracking**: Comprehensive project and milestone monitoring
- **Issue Management**: Create, read, update, and delete Linear issues

### Safety Features
- **Production Safety**: All write operations require `LINEAR_TEST_MODE=true`
- **Read-Only Default**: Safe for production use without modification risks
- **Error Handling**: Comprehensive error handling and validation

### API Capabilities
- **GraphQL Integration**: Efficient Linear API queries and mutations
- **Structured Data**: Type-safe data models and response handling
- **Batch Operations**: Support for bulk operations and workspace analysis

## Core Components

### LinearService Class
The main service class providing all Linear API functionality:

```python
from shared.services.linear_service import LinearService

linear_service = LinearService(
    api_key="your_linear_api_key",
    team_name="Your Team Name",
    default_assignee="user@example.com"
)
```

### Key Methods

#### Workspace Context
```python
# Get comprehensive workspace state
context = linear_service.get_workspace_context()
print(f"Projects: {len(context.projects)}")
print(f"Active Issues: {len(context.active_issues)}")
```

#### Issue Management
```python
# Create new issue (requires test mode)
issue_data = {
    "title": "Implement user authentication",
    "description": "Add secure login system",
    "priority": "2",
    "assignee": "developer@company.com"
}
created_issue = linear_service.create_issue(issue_data)

# Update existing issue (requires test mode)
update_data = {
    "title": "Updated task title",
    "status": "in_progress",
    "priority": "1"
}
updated_issue = linear_service.update_issue("issue-id", update_data)
```

#### Team Information
```python
# Get team by name
team = linear_service.get_team_by_name("SFAI Labs")
print(f"Team members: {len(team.members)}")

# Get team context with workflow states
team_context = linear_service.get_team_context(team.id)
```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `LINEAR_API_KEY` | Yes | Linear API key | None |
| `LINEAR_TEAM_NAME` | No | Default team name | "SFAI Labs" |
| `LINEAR_DEFAULT_ASSIGNEE` | No | Default assignee email | None |
| `LINEAR_TEST_MODE` | No | Enable write operations | false |

### Test Mode Safety

**Critical**: All write operations (create, update, delete) require test mode to be explicitly enabled:

```bash
export LINEAR_TEST_MODE=true
```

This safety feature prevents accidental modifications to your production Linear workspace.

## API Endpoints

The service runs on port 8002 with these endpoints:

- `GET /` - Service health check
- `POST /linear/workspace/context` - Get workspace context
- `POST /linear/issues/create` - Create new issue (test mode only)
- `PUT /linear/issues/{issue_id}` - Update issue (test mode only)
- `GET /linear/teams` - List all teams
- `GET /linear/projects` - List all projects

## Data Models

### LinearContext
```python
@dataclass
class LinearContext:
    teams: List[LinearTeam]
    projects: List[LinearProject]
    milestones: List[LinearMilestone]
    active_issues: List[LinearIssue]
    completed_issues: List[LinearIssue]
    workspace_summary: str
```

### LinearIssue
```python
@dataclass
class LinearIssue:
    id: str
    title: str
    description: str
    priority: int
    state: str
    assignee: Optional[str]
    created_at: datetime
    updated_at: datetime
    url: str
```

### LinearProject
```python
@dataclass
class LinearProject:
    id: str
    name: str
    description: str
    state: str
    progress: float
    target_date: Optional[datetime]
    team_names: List[str]
```

## Development

### Running the Service
```bash
# Start the linear service
uv run python services/linear/main.py

# Or using make
make run service=linear
```

### Testing
```bash
# Run Linear service tests
uv run python tests/test_slackbot_linear_integration.py

# Test specific Linear functionality
python -c "
from shared.services.linear_service import LinearService
service = LinearService('your_key', 'Your Team', None)
context = service.get_workspace_context()
print(f'Found {len(context.projects)} projects')
"
```

### Adding New Features
1. Add new methods to `LinearService` class
2. Update data models in `shared/core/models.py`
3. Add GraphQL queries/mutations as needed
4. Add comprehensive tests
5. Update API endpoints in `orchestrator.py`

## GraphQL Queries

The service uses GraphQL for efficient Linear API interactions:

### Workspace Query
```graphql
query {
  projects {
    nodes {
      id
      name
      description
      state
      progress
      targetDate
    }
  }
  teams {
    nodes {
      id
      name
      key
      members {
        nodes {
          id
          name
          email
        }
      }
    }
  }
}
```

### Issue Creation
```graphql
mutation CreateIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      title
      url
    }
  }
}
```

### Issue Update
```graphql
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      id
      title
      description
      state {
        name
      }
    }
  }
}
```

## Integration with Slackbot

The Linear service is deeply integrated with the Slackbot service:

1. **Real-time Context**: Provides current workspace state for all Slack commands
2. **Ticket Management**: Handles creation and updates from Slack commands
3. **Team Information**: Supplies team member data for Slack responses
4. **Project Status**: Provides project progress for summaries

## Security & Best Practices

### API Key Management
- Store API keys securely in environment variables
- Never commit API keys to version control
- Use service-specific API keys with minimal required permissions

### Rate Limiting
- The service respects Linear API rate limits
- Implements exponential backoff for failed requests
- Batches operations when possible

### Error Handling
- Comprehensive error handling for all API calls
- Graceful degradation when Linear API is unavailable
- Detailed error logging for debugging

### Production Safety
- All write operations require explicit test mode enablement
- Read-only operations are safe for production use
- Comprehensive validation before making API calls

## Troubleshooting

### Common Issues

**"Linear API request failed"**
- Verify `LINEAR_API_KEY` is valid and active
- Check network connectivity to Linear API
- Ensure API key has required permissions

**"Team not found"**
- Verify `LINEAR_TEAM_NAME` matches your workspace
- Check team name spelling and capitalization
- Ensure your API key has access to the team

**"CRITICAL SAFETY ERROR"**
- This is expected when trying to write without test mode
- Set `LINEAR_TEST_MODE=true` to enable write operations
- Only enable test mode when you intend to modify Linear data

**"GraphQL query failed"**
- Check GraphQL syntax in custom queries
- Verify all required fields are included
- Review Linear API documentation for schema changes

### Debug Mode
Enable verbose logging:
```bash
export LINEAR_DEBUG=true
export LINEAR_TEST_MODE=true  # Only if you want to test writes
```

## API Reference

For complete Linear API documentation, see:
- [Linear API Docs](https://developers.linear.app/docs)
- [GraphQL Schema](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)
- [Authentication](https://developers.linear.app/docs/graphql/working-with-the-graphql-api#authentication) 