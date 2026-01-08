# Dev MCP Server

A Model Context Protocol (MCP) server for OnceHub booking integration. This server provides tools to fetch available time slots and schedule meetings through the OnceHub API.

## Architecture
![Architecture](./images/mcp-work-flow.png)


## Project Structure

```
mcp-server/
├── main.py              # MCP server with tool definitions
├── models.py            # Pydantic models for BookingForm and Location
├── pyproject.toml       # Project dependencies and configuration
├── Dockerfile           # Docker image configuration
├── .dockerignore        # Files to exclude from Docker build
└── README.md            # This file
```


## Tools

### 1. `get_booking_time_slots`
Retrieves available time slots from a booking calendar.

**Parameters:**
- `calendar_id` (str): The booking calendar ID
- `api_key` (str): API key for authentication
- `start_time` (str, optional): Filter slots from this datetime (ISO format, e.g., '2024-01-15T09:00:00')
- `end_time` (str, optional): Filter slots until this datetime (ISO format, e.g., '2024-01-30T17:00:00')
- `timeout` (int, default: 30): Request timeout in seconds

**Returns:** Dictionary containing booking slots information with success status, time slots data, and metadata.

### 2. `schedule_meeting`
Schedules a meeting in a specified time slot.

**Parameters:**
- `calendar_id` (str): ID of the booking calendar
- `start_time` (str): The date and time of the time slot (ISO format)
- `guest_time_zone` (str): The guest's timezone in IANA format (e.g., 'America/New_York')
- `guest_name` (str): Guest's full name
- `guest_email` (str): Guest's email address
- `api_key` (str): API key for authentication
- `guest_phone` (str, optional): Guest's phone number
- `location_type` (str, optional): Type of location ("physical", "virtual", or "phone")
- `location_value` (str, optional): Location details (address, URL, or phone number)
- `string_custom_fields` (str, optional): Custom string fields
- `array_custom_fields` (list, optional): Custom array fields
- `timeout` (int, default: 30): Request timeout in seconds

**Returns:** Dictionary with booking confirmation details, booking ID, and meeting information.

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- OnceHub API key
- OnceHub API URL (defaults to `https://heisenbergapi.staticso2.com`)

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
```powershell
cd C:\Projects\mcp-server
```

### 3. Set environment variables (optional)
```powershell
$env:ONCEHUB_API_URL="https://heisenbergapi.staticso2.com"
```

Note: `ONCEHUB_API_KEY` Need to pas as header at client side.

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
```powershell
docker run -p 8000:8000 `
  -e ONCEHUB_API_URL="https://heisenbergapi.staticso2.com" `
  mcp-server
```

## Models

### `BookingForm`
Represents guest information for booking.

**Fields:**
- `name` (str): Guest's full name
- `email` (str): Guest's email address
- `phone` (str): Guest's phone number
- `string_custom_fields` (str): Custom string fields
- `array_custom_fields` (List[str]): Custom array fields

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

### Run with different log levels
Edit `main.py` and change `log_level` parameter:
```python
asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8000, log_level="debug"))
```

Available log levels: `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"`

## Client Configuration (VS Code/Copilot)

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

Add your license information here.

## Contributing

Add your contribution guidelines here.