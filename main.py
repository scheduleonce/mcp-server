import os
import asyncio
import httpx
import json
import logging
from typing import Annotated, Optional, Dict, Any
from pydantic import Field
from models import Location
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP(name = "mcp-server")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

@mcp.custom_route("/healthy", methods=["GET"])
async def healthy_check(request):
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

def get_api_key_from_context() -> str:
    """Extract API key from FastMCP context"""
    try:
        headers = get_http_headers()
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "").strip()
        raise ValueError("Missing or invalid Authorization header")
    except Exception as e:
        raise ValueError(f"Failed to get API key from context: {str(e)}")

@mcp.tool()
def get_booking_time_slots(
    calendar_id: Annotated[str, Field(..., description="The unique ID of the OnceHub booking calendar (e.g., 'BKC-XXXXXXXXXX')")],
    start_time: Annotated[Optional[str], Field(default=None, description="The start time for filtering available slots, in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SSZ')")] = None,
    end_time: Annotated[Optional[str], Field(default=None, description="The end time for filtering available slots, in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SSZ')")] = None,
    timeout: Annotated[int, Field(default=30, description="Maximum seconds to wait for the API response")] = 30
) -> Dict[str, Any]:
    """
    Retrieves a list of available booking time slots from a specific booking calendar. Use this tool before scheduling a meeting to ensure the desired time is valid.

    """
    try:
        # Get API key from context
        api_key = get_api_key_from_context()

        # if not base_url:
        base_url = os.getenv("ONCEHUB_API_URL", "https://api.oncehub.com")

        url = f"{base_url.rstrip('/')}/v2/booking-calendars/{calendar_id}/time-slots"

        # Prepare query parameters
        params = {}
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "API-key": api_key
        }
        
        # Log the outgoing request
        logger.info(f"→ GET {url}")
        
        # Make the HTTP request with proper query parameters
        with httpx.Client() as client:
            response = client.get(
                url=url,
                params=params,
                headers=headers,
                timeout=timeout
            )
        
        # Log the response
        logger.info(f"← Response status: {response.status_code}")
        
        # Parse response
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "url": url,
            "calendar_id": calendar_id,
            "filters": {
                "start_time": start_time,
                "end_time": end_time
            }
        }
        
        if response.status_code == 200:
            try:
                time_slots = response.json()
                result["data"] = time_slots
                result["total_slots"] = len(time_slots) if isinstance(time_slots, list) else 0
                
                # Add metadata
                if isinstance(time_slots, list) and time_slots:
                    result["metadata"] = {
                        "time_slots": time_slots
                        }
                    
            except json.JSONDecodeError:
                result["data"] = response.text
                result["error"] = "Response is not valid JSON"
                result["total_slots"] = 0
                
        else:
            try:
                error_data = response.json()
                result["error"] = error_data.get("message", f"HTTP {response.status_code}")
                result["error_details"] = error_data
            except json.JSONDecodeError:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
        
        return result
        
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "user_friendly_error": "API key not configured.",
            "status_code": None,
            "calendar_id": calendar_id
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Request timed out after {timeout} seconds",
            "status_code": None,
            "calendar_id": calendar_id
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "status_code": None,
            "calendar_id": calendar_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "status_code": None,
            "calendar_id": calendar_id
        }

@mcp.tool()
def schedule_meeting(
    calendar_id: Annotated[str, Field(..., description="The unique ID of the OnceHub booking calendar (e.g., 'BKC-XXXXXXXXXX')")],
    start_time: Annotated[str, Field(..., description="The exact start time of the slot in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)")],
    guest_time_zone: Annotated[str, Field(..., description="The guest's time zone in IANA format (e.g., 'America/New_York', 'Europe/London')")],
    guest_name: Annotated[str, Field(..., description="Full name of the guest")],
    guest_email: Annotated[str, Field(..., description="Email address for confirmation")],
    guest_phone: Annotated[Optional[str], Field(default=None, description="The guest's phone number in E.164 format (e.g., '+15551234567')")] = None,
    location_type: Annotated[Optional[str], Field(default=None, description="The mode of the meeting. Allowed values: 'virtual', 'virtual_static', 'physical', 'guest_phone'. Values should match the options available in the relevant time slot result.")] = None,
    location_value: Annotated[Optional[str], Field(default=None, description="Context-specific value based on location_type: If virtual: Specify the selected provider name (e.g., 'google_meet', 'microsoft_teams', 'gotomeeting', 'webex', or 'zoom'). If virtual_static: Use null. If physical: Provide the Address ID (e.g., 'ADD-XXXXXXXXXX'). If phone: Provide the phone number in E164 format.")] = None,
    timeout: Annotated[int, Field(default=30, description="Maximum seconds to wait for the API response")] = 30,
    custom_fields: Annotated[Optional[dict], Field(default=None, description="Key-value pairs for the booking form. Example: {'company': 'Acme', 'interests': ['Pricing', 'Demo']}")] = None  # Accept any additional fields as custom fields
) -> dict:
    """
    Books a meeting in a specific time slot and before that you must identify a valid start_time using get_booking_time_slots before calling this tool.
    """
    try:
        # Get API key from context
        api_key = get_api_key_from_context()
        
        # if not base_url:
        base_url = os.getenv("ONCEHUB_API_URL", "https://api.oncehub.com")
        
        # Construct the endpoint URL
        url = f"{base_url.rstrip('/')}/v2/booking-calendars/{calendar_id}/schedule"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "API-key": api_key
        }

        booking_form_data = {
            "name": guest_name,
            "email": guest_email,
            "phone": guest_phone
        }

        # Add all custom fields directly to booking_form as key-value pairs
        if custom_fields and isinstance(custom_fields, dict):  # Added isinstance check
            logger.info(f"Adding custom fields: {json.dumps(custom_fields, indent=2)}")
            booking_form_data.update(custom_fields)
        
        # Prepare the booking payload
        booking_data = {
            "start_time": start_time,
            "guest_time_zone": guest_time_zone,
            "booking_form": booking_form_data
        }
        
        # Add location details if provided
        if location_type and location_value:
            booking_data["location"] = Location(
                type=location_type,
                value=location_value
            ).to_dict()
        
        # Log the outgoing request
        logger.info(f"→ POST {url}")
        
        # Make the HTTP request
        with httpx.Client() as client:
            response = client.post(
                url=url,
                json=booking_data,
                headers=headers,
                timeout=timeout
            )
        
        # Log the response
        logger.info(f"← Response status: {response.status_code}")
        
        # Parse response
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "url": url,
            "calendar_id": calendar_id,
            "booking_request": booking_data
        }
        
        if response.status_code == 200:
            try:
                booking_response = response.json()
                result["booking_id"] = booking_response.get("id")
                result["meeting_details"] = booking_response
                
                # Add confirmation details
                result["confirmation"] = {
                    "guest_name": guest_name,
                    "guest_email": guest_email,
                    "guest_phone": guest_phone,
                    "scheduled_time": start_time,
                    "timezone": guest_time_zone,
                    "location_type": location_type,
                    "location_value": location_value,
                    "booking_id": booking_response.get("id")
                }
                    
            except json.JSONDecodeError:
                result["meeting_details"] = response.text
                result["error"] = "Response is not valid JSON"
                
        else:
            try:
                error_data = response.json()
                result["error"] = error_data.get("message", f"HTTP {response.status_code}")
                result["error_details"] = error_data
                
                if response.status_code == 400:
                    result["user_friendly_error"] = "Invalid booking details. Please check the time slot and guest information."
                elif response.status_code == 401:
                    result["user_friendly_error"] = "Authentication failed. Please check if the API key is valid."
                elif response.status_code == 404:
                    result["user_friendly_error"] = f"Calendar '{calendar_id}' not found."
                elif response.status_code >= 500:
                    result["user_friendly_error"] = "Server error occurred. Please try again later."
                    
            except json.JSONDecodeError:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
        
        return result
        
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "user_friendly_error": "API key not configured.",
            "status_code": None,
            "calendar_id": calendar_id
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Request timed out after {timeout} seconds",
            "user_friendly_error": "The booking request timed out. Please try again.",
            "status_code": None,
            "calendar_id": calendar_id
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "user_friendly_error": "Failed to connect to the booking service.",
            "status_code": None,
            "calendar_id": calendar_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "user_friendly_error": f"An unexpected error occurred: {str(e)}",
            "status_code": None,
            "calendar_id": calendar_id
        }

if __name__ == "__main__":
    asyncio.run(mcp.run_async(transport="sse", host="0.0.0.0", port=8000))