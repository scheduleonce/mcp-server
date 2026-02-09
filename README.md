# OnceHub MCP Server

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen.svg)]()
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

A Model Context Protocol (MCP) server for OnceHub booking integration. This server provides AI assistants with tools to fetch available time slots and schedule meetings through the OnceHub API.

**Compatible with:** VS Code Copilot, Claude Desktop, OpenAI, and any MCP-compatible AI client.

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Tools](#tools)
- [Installation](#installation--running-locally-with-uv)
- [Testing](#testing)
- [Client Configuration](#client-configuration)
- [Production Deployment](#production-deployment)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔌 **MCP Protocol Support** - Works with any MCP-compatible AI client
- 📅 **Time Slot Retrieval** - Fetch available booking slots from OnceHub calendars
- 🗓️ **Meeting Scheduling** - Automatically schedule meetings with guest information
- 🔐 **Secure Authentication** - API key-based authentication via headers
- 🧪 **Well Tested** - 92% code coverage with comprehensive unit tests
- 🐳 **Docker Ready** - Containerized for easy deployment
- 📝 **AI-Friendly Prompts** - Built-in workflow guidance for AI assistants

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/scheduleonce/mcp-server.git
cd mcp-server

# 2. Set environment variable
export ONCEHUB_API_URL="https://api.oncehub.com"  # Or your OnceHub API endpoint

# 3. Run the server
uv run main.py

# 4. Test the server
curl http://localhost:8000/health
```

The server will be available at `http://localhost:8000/sse` for MCP clients.

## Architecture
![Architecture](./images/mcp-server_architecture.png)


## Project Structure

```
mcp-server/
├── main.py              # MCP server with tool definitions
├── models.py            # Pydantic data schemas for BookingForm and Location
├── pyproject.toml       # Project dependencies and configuration
├── Dockerfile           # Docker image configuration
├── .dockerignore        # Files to exclude from Docker build
└── README.md            # This file
```


## Tools

### 1. `get_booking_time_slots`
Retrieves available time slots from a booking calendar.

**Parameters:**
- `calendar_id` (str, required): The booking calendar ID (e.g., 'BKC-XXXXXXXXXX')
- `start_time` (str, optional): Filter slots from this datetime in ISO 8601 format (e.g., '2026-02-15T09:00:00Z')
- `end_time` (str, optional): Filter slots until this datetime in ISO 8601 format (e.g., '2026-02-28T17:00:00Z')
- `timeout` (int, default: 30): Request timeout in seconds

**Example Response:**
```json
{
  "success": true,
  "status_code": 200,
  "calendar_id": "BKC-XXXXXXXXXX",
  "total_slots": 5,
  "data": [
    {"start_time": "2026-02-10T10:00:00Z", "end_time": "2026-02-10T11:00:00Z"},
    {"start_time": "2026-02-10T14:00:00Z", "end_time": "2026-02-10T15:00:00Z"}
  ]
}
```

### 2. `schedule_meeting`
Schedules a meeting in a specified time slot. **Always call `get_booking_time_slots` first** to ensure the time slot is available.

**Parameters:**
- `calendar_id` (str, required): ID of the booking calendar (e.g., 'BKC-XXXXXXXXXX')
- `start_time` (str, required): The exact start time from an available slot in ISO 8601 format
- `guest_time_zone` (str, required): Guest's timezone in IANA format (e.g., 'America/New_York', 'Europe/London')
- `guest_name` (str, required): Guest's full name
- `guest_email` (str, required): Guest's email address for confirmation
- `guest_phone` (str, optional): Guest's phone number in E.164 format (e.g., '+15551234567')
- `location_type` (str, optional): Meeting mode - 'virtual', 'virtual_static', 'physical', or 'guest_phone'
- `location_value` (str, optional): Location details based on type:
  - `virtual`: Provider name (e.g., 'zoom', 'google_meet', 'microsoft_teams')
  - `virtual_static`: Use null
  - `physical`: Address ID (e.g., 'ADD-XXXXXXXXXX')
  - `guest_phone`: Phone number in E.164 format
- `custom_fields` (dict, optional): Custom form fields as key-value pairs (e.g., `{"company": "Acme", "interests": ["Demo"]}`)
- `timeout` (int, default: 30): Request timeout in seconds

**Example Response:**
```json
{
  "success": true,
  "status_code": 200,
  "booking_id": "BKG-123456789",
  "confirmation": {
    "guest_name": "John Doe",
    "guest_email": "john@example.com",
    "scheduled_time": "2026-02-10T10:00:00Z",
    "timezone": "America/New_York"
  }
}
```

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- OnceHub API key - See [Authentication documentation](https://developers.oncehub.com/docs/overview/authentication/) to obtain your API key
- OnceHub API endpoint URL (usually `https://api.oncehub.com`)

## Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required: Your OnceHub API endpoint
ONCEHUB_API_URL=https://api.oncehub.com

# Note: API key is passed via Authorization header from MCP clients
# Do NOT commit API keys to version control
```

## Installation & Running Locally with uv

### 1. Install uv (if not already installed)

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the repository
```bash
git clone https://github.com/scheduleonce/mcp-server.git
cd mcp-server
```

### 3. Set environment variables

**Windows (PowerShell):**
```powershell
$env:ONCEHUB_API_URL="https://api.oncehub.com"
```

**macOS/Linux:**
```bash
export ONCEHUB_API_URL="https://api.oncehub.com"
```

**Or create a `.env` file:**
```bash
echo "ONCEHUB_API_URL=https://api.oncehub.com" > .env
```

> **Note:** The API key is passed via the `Authorization` header from MCP clients (not as an environment variable).

### 4. Run the server using uv

**Option 1: Direct execution**
```powershell
uv run main.py
```

**Option 2: Using the script entry point**
```powershell
uv run mcp-server
```

The server will start on `http://0.0.0.0:8000`

### 5. Verify the server is running

**Health check:**
```powershell
curl http://localhost:8000/health
```

**Connect to SSE endpoint:**
```powershell
curl http://localhost:8000/sse
```

## Running with Docker

### Build the Docker image
```powershell
docker build -t mcp-server .
```

### Run the container
```powershell
docker run -p 8000:8000 mcp-server
```

### With environment variables
```bash
docker run -p 8000:8000 \
  -e ONCEHUB_API_URL="https://api.oncehub.com" \
  mcp-server
```

### Using Docker Compose (recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ONCEHUB_API_URL=https://api.oncehub.com
    restart: unless-stopped
```

Then run:
```bash
docker-compose up -d
```

## Data Schemas

### `Location`
Represents meeting location details.

**Fields:**
- `type` (str): Location type ("physical", "virtual", "phone")
- `value` (str): Location details (address, URL, phone number)

## Logging

The server includes comprehensive logging for HTTP requests to OnceHub:
- Outgoing requests (→)
- Response status codes (←)
- Request/response bodies

Logs are output to the console with timestamps and log levels.

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /sse` - Server-Sent Events endpoint for MCP protocol communication

## Development

### Install dependencies manually
```powershell
uv pip install fastmcp pydantic httpx
```

### Install test dependencies
```powershell
uv pip install -e ".[test]"
```

### Run with different log levels
Edit `main.py` and change `log_level` parameter:
```python
asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8000, log_level="debug"))
```

Available log levels: `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"`

## Testing

The project includes comprehensive unit tests for all tools and functions.

### Install Test Dependencies

```powershell
# Install test dependencies
uv pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Run Tests

**Run all tests:**
```bash
uv run pytest
```

**Run tests with coverage report:**
```bash
uv run pytest --cov=. --cov-report=html --cov-report=term
```

**Run specific test file:**
```bash
uv run pytest test_tools.py
```

**Run specific test class:**
```bash
uv run pytest test_tools.py::TestGetBookingTimeSlots
```

**Run specific test:**
```bash
uv run pytest test_tools.py::TestGetBookingTimeSlots::test_get_time_slots_success
```

**Run with verbose output:**
```bash
uv run pytest -v
```

**Run and stop on first failure:**
```bash
uv run pytest -x
```

### Test Coverage

After running tests with coverage, open the HTML report:
```powershell
# Windows
start htmlcov/index.html

# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

### Test Structure

- `test_tools.py` - Unit tests for all tool functions
  - `TestGetApiKeyFromContext` - Tests for API key extraction
  - `TestGetBookingTimeSlots` - Tests for time slot retrieval
  - `TestScheduleMeeting` - Tests for meeting scheduling

All tests use mocking to avoid actual API calls and ensure fast, reliable test execution.

## Client Configuration

This MCP server is compatible with **VS Code Copilot**, **OpenAI**, and other MCP-compatible clients.

### Connecting VS Code or GitHub Copilot

To connect your VS Code or GitHub Copilot client to the MCP server:

### 1. Create MCP Configuration File

Create a file named `mcp.json` in your workspace's `.vscode` folder:

```bash
# Create .vscode directory if it doesn't exist
mkdir .vscode

# Create mcp.json file
# On Windows PowerShell:
New-Item -Path ".vscode\mcp.json" -ItemType File -Force

# On macOS/Linux:
touch .vscode/mcp.json
```

### 2. Add Server Configuration

Add the following configuration to `.vscode/mcp.json`:

```json
{
  "servers": {
    "my-mcp-server": {
      "url": "http://0.0.0.0:8000/sse",
      "type": "http",
      "headers": {
        "authorization": "Bearer YOUR_ONCEHUB_API_KEY"
      }
    }
  },
  "inputs": []
}
```

**Important:** Replace `YOUR_ONCEHUB_API_KEY` with your actual OnceHub API key.

### 3. Start/Restart the MCP Client

- **For VS Code**: Reload the window (`Ctrl+Shift+P` or `Cmd+Shift+P` → "Developer: Reload Window")
- **For GitHub Copilot**: Restart the GitHub Copilot extension or reload VS Code

### 4. Verify Connection

The MCP server should now be available to your AI assistant. You can verify by:
- Checking that the server is running at `http://localhost:8000/health`
- Testing a tool call like `get_booking_time_slots` through your AI assistant

## Production Deployment

### Security Best Practices

1. **API Key Management**
   - Never commit API keys to version control
   - Use environment variables or secret management systems
   - Rotate API keys regularly

2. **Network Security**
   - Use HTTPS in production (add reverse proxy like nginx)
   - Implement rate limiting to prevent abuse
   - Use firewall rules to restrict access

3. **Monitoring**
   - Monitor the `/health` endpoint for availability
   - Set up logging aggregation (e.g., ELK stack, CloudWatch)
   - Track API response times and error rates

### Deployment Options

#### Docker Deployment
```bash
# Build and tag the image
docker build -t oncehub-mcp-server:1.0.0 .

# Run with restart policy
docker run -d \
  --name oncehub-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  -e ONCEHUB_API_URL="https://api.oncehub.com" \
  oncehub-mcp-server:1.0.0
```

#### Cloud Deployment
- **AWS**: Use ECS, Fargate, or EC2 with Application Load Balancer
- **Azure**: Deploy to Azure Container Instances or App Service
- **GCP**: Use Cloud Run or Google Kubernetes Engine

### Performance Considerations

- Default timeout is 30 seconds - adjust based on your needs
- The server uses asyncio for concurrent request handling
- Consider horizontal scaling for high-traffic scenarios
- Use connection pooling for database/cache if added

### Health Monitoring

```bash
# Simple health check script
curl -f http://localhost:8000/health || exit 1

# Docker healthcheck (add to Dockerfile)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

## Troubleshooting

### Error: "API key is required"
Ensure you're passing the `api_key` parameter when calling the tools.

### Error: "404 Not Found" on `/health`
Make sure the server is running and accessible on port 8000.

### Error: "405 Method Not Allowed" on `/sse`
The SSE endpoint requires a GET request, not POST. Use proper MCP client libraries or curl with GET.

### No logs showing for OnceHub requests
Check that logging is properly configured in `main.py` and the server is running with `log_level="info"` or `"debug"`.

## License

This project is licensed under the terms of the MIT open source license. Please refer to [MIT](LICENSE) for the full terms.

## Support

- **Documentation**: [OnceHub API Docs](https://developers.oncehub.com)
- **Issues**: [GitHub Issues](https://github.com/scheduleonce/mcp-server/issues)
- **MCP Protocol**: [Model Context Protocol](https://modelcontextprotocol.io)

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Compatible with the [Model Context Protocol](https://modelcontextprotocol.io)
- Powered by [OnceHub API](https://developers.oncehub.com)

---

**Made by the ScheduleOnce team**