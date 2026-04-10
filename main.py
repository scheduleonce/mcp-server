import asyncio
import logging
from typing import Any
from fastapi.responses import JSONResponse
from fastmcp import Client, FastMCP
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


def _to_dict(tool: Any) -> dict[str, Any]:
    """Convert tool metadata objects to dictionaries in a version-safe way."""
    if isinstance(tool, dict):
        return tool

    # Guard against unittest.mock objects, which claim any attribute via __getattr__.
    model_dump = getattr(tool, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    return {
        "name": getattr(tool, "name", None),
        "description": getattr(tool, "description", None),
        "inputSchema": getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None),
        "outputSchema": getattr(tool, "outputSchema", None) or getattr(tool, "output_schema", None),
    }


@mcp.custom_route("/tools", methods=["GET"])
async def tools_list(request):
    """Return registered MCP tools with description and parameter requirements."""
    try:
        async with Client(mcp) as client:
            tools = await client.list_tools()

        serialized_tools = []
        for tool in tools:
            tool_data = _to_dict(tool)
            input_schema = tool_data.get("inputSchema") or {}
            properties = input_schema.get("properties") or {}
            required_fields = input_schema.get("required") or []

            parameters = []
            for param_name, param_schema in properties.items():
                parameters.append(
                    {
                        "name": param_name,
                        "type": param_schema.get("type"),
                        "description": param_schema.get("description"),
                        "required": param_name in required_fields,
                    }
                )

            serialized_tools.append(
                {
                    "name": tool_data.get("name"),
                    "description": tool_data.get("description"),
                    "required_parameters": required_fields,
                    "parameters": parameters,
                    "input_schema": input_schema,
                }
            )

        return JSONResponse(
            {
                "success": True,
                "total_tools": len(serialized_tools),
                "tools": serialized_tools,
            }
        )
    except Exception as e:
        logger.exception("Failed to list tools")
        return JSONResponse(
            {
                "success": False,
                "error": f"Failed to list tools: {str(e)}",
            },
            status_code=500,
        )

# Register tools
mcp.tool()(get_booking_time_slots)
mcp.tool()(schedule_meeting)

if __name__ == "__main__":
    asyncio.run(mcp.run_async(transport="sse", host="0.0.0.0", port=8000))