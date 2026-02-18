import asyncio
import logging
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from tools import get_booking_time_slots, schedule_meeting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP(name = "mcp-server")

@mcp.custom_route("/health", methods=["GET"])
@mcp.custom_route("/healthy", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

# Register tools
mcp.tool()(get_booking_time_slots)
mcp.tool()(schedule_meeting)

if __name__ == "__main__":
    asyncio.run(mcp.run_async(transport="sse", host="0.0.0.0", port=8000))