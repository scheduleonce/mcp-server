import os
from fastmcp import FastMCP
import asyncio
import httpx
import json
import logging
from typing import Optional, Dict, Any
from models import BookingForm, Location
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP(name = "dev-mcp-server")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "service": "dev-mcp-server"})

@mcp.custom_route("/sse", methods=["POST"])
async def sse_post_handler(request):
    """Handle incorrect POST requests to SSE endpoint"""
    return JSONResponse(
        {"error": "SSE endpoint requires GET method, not POST"},
        status_code=405
    )

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def get_booking_time_slots(
    calendar_id: str,
    api_key: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Retrieve all available time slots from an OnceHub booking calendar.
    
    Use this tool to fetch open time slots that customers can book. You can optionally filter 
    the results by specifying a date/time range using start_time and end_time parameters.
    
    Args:
        calendar_id: The unique identifier of the OnceHub booking calendar. 
                    This ID identifies which calendar's time slots to fetch.
                    Example: "abc123-calendar-id"
        
        api_key: Your OnceHub API authentication key. Required for every request.
                This should be kept secure and not shared publicly.
        
        start_time: (Optional) Only return time slots starting from this date/time onwards.
                   Format: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)
                   Example: "2024-01-15T09:00:00" for January 15, 2024 at 9:00 AM
                   If omitted, returns slots from the current date onwards.
        
        end_time: (Optional) Only return time slots up until this date/time.
                 Format: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)
                 Example: "2024-01-30T17:00:00" for January 30, 2024 at 5:00 PM
                 If omitted, returns slots up to the calendar's configured availability limit.
        
        timeout: Maximum seconds to wait for the API response before timing out.
                Default is 30 seconds. Increase if dealing with slow network connections.
    
    Returns:
        A dictionary containing:
        - success (bool): Whether the request was successful
        - status_code (int): HTTP response status code
        - data (list): Array of available time slot objects with details
        - total_slots (int): Number of available slots returned
        - metadata (dict): Additional information about the slots
        - error (str): Error message if the request failed
    
    Example:
        get_booking_time_slots(
            calendar_id="cal_abc123",
            api_key="your_api_key_here",
            start_time="2024-12-01T00:00:00",
            end_time="2024-12-31T23:59:59"
        )
    """
    try:
        if not api_key:
            raise ValueError("API key is required for every request.")
        # Construct the endpoint URL

        # if not base_url:
        base_url = os.getenv("ONCEHUB_API_URL", "https://heisenbergapi.staticso2.com")

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
                    location_type_counts = {}
                    earliest_slot = None
                    latest_slot = None
                    
                    for slot in time_slots:
                        locations = slot.get("locations", [])
                        for location in locations:
                            loc_type = location.get("type", "unknown")
                            location_type_counts[loc_type] = location_type_counts.get(loc_type, 0) + 1
                    
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
            "user_friendly_error": "API key not configured. Please set ONCEHUB_API_KEY environment variable.",
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
    calendar_id: str,
    start_time: str,
    guest_time_zone: str,
    guest_name: str,
    guest_email: str,
    api_key: str,
    guest_phone: Optional[str] = None,
    location_type: Optional[str] = None,
    location_value: Optional[str] = None,
    string_custom_fields: Optional[str] = None,
    array_custom_fields: Optional[list] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Book a meeting in a specific time slot on an OnceHub calendar.
    
    Use this tool to schedule a new meeting/appointment for a guest at a specific date and time.
    This will reserve the time slot and send confirmation to the guest's email.
    
    Args:
        calendar_id: The unique identifier of the OnceHub booking calendar where the 
                    meeting should be scheduled.
                    Example: "cal_abc123"
        
        start_time: The exact date and time when the meeting should start.
                   Format: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)
                   Example: "2024-01-15T14:30:00" for January 15, 2024 at 2:30 PM
                   This must be one of the available time slots from get_booking_time_slots.
        
        guest_time_zone: The timezone of the guest in IANA timezone format.
                        This ensures times are displayed correctly to the guest.
                        Examples: "America/New_York", "Europe/London", "Asia/Tokyo", "UTC"
                        Find valid timezones at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        
        guest_name: The full name of the person booking the meeting.
                   Example: "John Smith" or "Jane Doe"
        
        guest_email: The email address of the guest. Meeting confirmation and details 
                    will be sent to this email address.
                    Example: "john.smith@example.com"
        
        api_key: Your OnceHub API authentication key. Required for every request.
                This should be kept secure and not shared publicly.
        
        guest_phone: (Optional) The guest's phone number for contact purposes.
                    Example: "+1-555-123-4567" or "555-123-4567"
        
        location_type: (Optional) Specifies how the meeting will be conducted.
                      Valid values:
                      - "virtual": Online meeting (e.g., Zoom, Teams, Google Meet)
                      - "physical": In-person meeting at a physical address
                      - "phone": Phone call meeting
        
        location_value: (Optional) The location details based on location_type:
                       - For "virtual": Meeting URL or join link (e.g., "https://zoom.us/j/123456")
                       - For "physical": Street address (e.g., "123 Main St, New York, NY 10001")
                       - For "phone": Phone number to call (e.g., "+1-555-123-4567")
        
        string_custom_fields: (Optional) Additional custom text information required by your 
                             booking form. Format depends on your OnceHub calendar configuration.
        
        array_custom_fields: (Optional) Additional custom multi-value information as a list.
                            Format: ["value1", "value2", "value3"]
                            Structure depends on your OnceHub calendar configuration.
        
        timeout: Maximum seconds to wait for the API response before timing out.
                Default is 30 seconds. Increase if dealing with slow network connections.
    
    Returns:
        A dictionary containing:
        - success (bool): Whether the booking was successful
        - status_code (int): HTTP response status code
        - booking_id (str): Unique identifier for the created booking
        - meeting_details (dict): Complete meeting information from OnceHub
        - confirmation (dict): Summary of booking details including guest info, time, and location
        - error (str): Error message if the booking failed
        - user_friendly_error (str): Human-readable error explanation
    
    Example:
        schedule_meeting(
            calendar_id="cal_abc123",
            start_time="2024-01-15T14:30:00",
            guest_time_zone="America/New_York",
            guest_name="John Smith",
            guest_email="john.smith@example.com",
            api_key="your_api_key_here",
            guest_phone="+1-555-123-4567",
            location_type="virtual",
            location_value="https://zoom.us/j/123456789"
        )
    """
    try:
        if not api_key:
            raise ValueError("API key is required for every request.")
        
        # if not base_url:
        base_url = os.getenv("ONCEHUB_API_URL", "https://heisenbergapi.staticso2.com")
        
        # Construct the endpoint URL
        url = f"{base_url.rstrip('/')}/v2/booking-calendars/{calendar_id}/schedule"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "API-key": api_key
        }
        
        # Create BookingForm
        booking_form = BookingForm(
            name=guest_name,
            email=guest_email,
            phone=guest_phone or "",
            string_custom_fields=string_custom_fields or "",
            array_custom_fields=array_custom_fields or []
        )
        
        # Prepare the booking payload
        booking_data = {
            "start_time": start_time,
            "guest_time_zone": guest_time_zone,
            "booking_form": booking_form.to_dict()
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
            "user_friendly_error": "API key not configured. Please set ONCEHUB_API_KEY environment variable.",
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
    asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8000, log_level="info"))