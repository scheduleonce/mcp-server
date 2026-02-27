import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
import httpx
from tools import get_booking_time_slots, schedule_meeting, get_api_key_from_context


class TestGetApiKeyFromContext:
    """Test cases for get_api_key_from_context function"""
    
    @patch('tools.get_http_headers')
    def test_get_api_key_success(self, mock_get_headers):
        """Test successful API key extraction"""
        mock_get_headers.return_value = {"authorization": "Bearer test-api-key-123"}
        result = get_api_key_from_context()
        assert result == "test-api-key-123"
    
    @patch('tools.get_http_headers')
    def test_get_api_key_missing_bearer(self, mock_get_headers):
        """Test when authorization header doesn't have Bearer prefix"""
        mock_get_headers.return_value = {"authorization": "test-api-key-123"}
        with pytest.raises(ValueError, match="Missing or invalid Authorization header"):
            get_api_key_from_context()
    
    @patch('tools.get_http_headers')
    def test_get_api_key_missing_header(self, mock_get_headers):
        """Test when authorization header is missing"""
        mock_get_headers.return_value = {}
        with pytest.raises(ValueError, match="Missing or invalid Authorization header"):
            get_api_key_from_context()
    
    @patch('tools.get_http_headers')
    def test_get_api_key_exception(self, mock_get_headers):
        """Test when get_http_headers raises an exception"""
        mock_get_headers.side_effect = Exception("Context error")
        with pytest.raises(ValueError, match="Failed to get API key from context"):
            get_api_key_from_context()


class TestGetBookingTimeSlots:
    """Test cases for get_booking_time_slots function"""
    
    @pytest.fixture
    def mock_env(self):
        """Set up environment variables"""
        with patch.dict(os.environ, {"ONCEHUB_API_URL": "https://api.oncehub.com"}):
            yield
    
    @pytest.fixture
    def mock_api_key(self):
        """Mock the API key context"""
        with patch('tools.get_api_key_from_context', return_value="test-api-key"):
            yield
    
    def test_get_time_slots_success(self, mock_env, mock_api_key):
        """Test successful retrieval of time slots"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"start_time": "2026-02-10T10:00:00Z", "end_time": "2026-02-10T11:00:00Z"},
            {"start_time": "2026-02-10T14:00:00Z", "end_time": "2026-02-10T15:00:00Z"}
        ]
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = get_booking_time_slots(calendar_id="BKC-TEST123")
            
            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["calendar_id"] == "BKC-TEST123"
            assert result["total_slots"] == 2
            assert len(result["data"]) == 2
    
    def test_get_time_slots_with_filters(self, mock_env, mock_api_key):
        """Test retrieval with start and end time filters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        with patch('httpx.Client') as mock_client:
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.return_value = mock_response
            
            result = get_booking_time_slots(
                calendar_id="BKC-TEST123",
                start_time="2026-02-10T00:00:00Z",
                end_time="2026-02-15T00:00:00Z"
            )
            
            # Verify parameters were passed
            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["start_time"] == "2026-02-10T00:00:00Z"
            assert call_args.kwargs["params"]["end_time"] == "2026-02-15T00:00:00Z"
            assert result["success"] is True
    
    def test_get_time_slots_missing_api_url(self, mock_api_key):
        """Test when ONCEHUB_API_URL is not set"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_booking_time_slots(calendar_id="BKC-TEST123")
            
            assert result["success"] is False
            assert "ONCEHUB_API_URL environment variable is not set" in result["error"]
            assert result["status_code"] is None
    
    def test_get_time_slots_missing_api_key(self, mock_env):
        """Test when API key is not available"""
        with patch('tools.get_api_key_from_context', side_effect=ValueError("API key not configured")):
            result = get_booking_time_slots(calendar_id="BKC-TEST123")
            
            assert result["success"] is False
            assert "API key not configured" in result["error"]
            assert result["status_code"] is None
    
    def test_get_time_slots_http_error(self, mock_env, mock_api_key):
        """Test handling of HTTP error responses"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Calendar not found"}
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = get_booking_time_slots(calendar_id="BKC-NOTFOUND")
            
            assert result["success"] is False
            assert result["status_code"] == 404
            assert "Calendar not found" in result["error"]
    
    def test_get_time_slots_timeout(self, mock_env, mock_api_key):
        """Test handling of timeout"""
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
            
            result = get_booking_time_slots(calendar_id="BKC-TEST123", timeout=5)
            
            assert result["success"] is False
            assert "timed out after 5 seconds" in result["error"]
    
    def test_get_time_slots_request_error(self, mock_env, mock_api_key):
        """Test handling of request errors"""
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Connection failed")
            
            result = get_booking_time_slots(calendar_id="BKC-TEST123")
            
            assert result["success"] is False
            assert "Request failed" in result["error"]
    
    def test_get_time_slots_invalid_json(self, mock_env, mock_api_key):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Not a JSON response"
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = get_booking_time_slots(calendar_id="BKC-TEST123")
            
            assert result["success"] is True  # Still success status code
            assert "Response is not valid JSON" in result["error"]
            assert result["total_slots"] == 0


class TestScheduleMeeting:
    """Test cases for schedule_meeting function"""
    
    @pytest.fixture
    def mock_env(self):
        """Set up environment variables"""
        with patch.dict(os.environ, {"ONCEHUB_API_URL": "https://api.oncehub.com"}):
            yield
    
    @pytest.fixture
    def mock_api_key(self):
        """Mock the API key context"""
        with patch('tools.get_api_key_from_context', return_value="test-api-key"):
            yield
    
    @pytest.fixture
    def booking_params(self):
        """Common booking parameters"""
        return {
            "calendar_id": "BKC-TEST123",
            "start_time": "2026-02-10T10:00:00Z",
            "guest_time_zone": "America/New_York",
            "guest_name": "John Doe",
            "guest_email": "john.doe@example.com"
        }
    
    def test_schedule_meeting_success(self, mock_env, mock_api_key, booking_params):
        """Test successful meeting scheduling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "BKG-123456",
            "start_time": "2026-02-10T10:00:00Z",
            "status": "confirmed"
        }
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["booking_id"] == "BKG-123456"
            assert result["confirmation"]["guest_name"] == "John Doe"
            assert result["confirmation"]["guest_email"] == "john.doe@example.com"
    
    def test_schedule_meeting_with_phone(self, mock_env, mock_api_key, booking_params):
        """Test scheduling with phone number"""
        booking_params["guest_phone"] = "+15551234567"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "BKG-123456"}
        
        with patch('httpx.Client') as mock_client:
            mock_post = mock_client.return_value.__enter__.return_value.post
            mock_post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            # Verify phone was included in the request
            call_args = mock_post.call_args
            booking_data = call_args.kwargs["json"]
            assert booking_data["booking_form"]["phone"] == "+15551234567"
            assert result["success"] is True
    
    def test_schedule_meeting_with_location(self, mock_env, mock_api_key, booking_params):
        """Test scheduling with location"""
        booking_params["location_type"] = "virtual"
        booking_params["location_value"] = "zoom"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "BKG-123456"}
        
        with patch('httpx.Client') as mock_client:
            mock_post = mock_client.return_value.__enter__.return_value.post
            mock_post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            # Verify location was included
            call_args = mock_post.call_args
            booking_data = call_args.kwargs["json"]
            assert "location" in booking_data
            assert booking_data["location"]["type"] == "virtual"
            assert booking_data["location"]["value"] == "zoom"
            assert result["success"] is True
    
    def test_schedule_meeting_with_custom_fields(self, mock_env, mock_api_key, booking_params):
        """Test scheduling with custom fields"""
        booking_params["custom_fields"] = {
            "company": "Acme Corp",
            "interests": ["Pricing", "Demo"]
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "BKG-123456"}
        
        with patch('httpx.Client') as mock_client:
            mock_post = mock_client.return_value.__enter__.return_value.post
            mock_post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            # Verify custom fields were included
            call_args = mock_post.call_args
            booking_data = call_args.kwargs["json"]
            assert booking_data["booking_form"]["company"] == "Acme Corp"
            assert booking_data["booking_form"]["interests"] == ["Pricing", "Demo"]
            assert result["success"] is True
    
    def test_schedule_meeting_missing_api_url(self, mock_api_key, booking_params):
        """Test when ONCEHUB_API_URL is not set"""
        with patch.dict(os.environ, {}, clear=True):
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert "ONCEHUB_API_URL environment variable is not set" in result["error"]
    
    def test_schedule_meeting_missing_api_key(self, mock_env, booking_params):
        """Test when API key is not available"""
        with patch('tools.get_api_key_from_context', side_effect=ValueError("API key not configured")):
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert "API key not configured" in result["error"]
    
    def test_schedule_meeting_bad_request(self, mock_env, mock_api_key, booking_params):
        """Test handling of 400 Bad Request"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid time slot"}
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert result["status_code"] == 400
            assert "Invalid time slot" in result["error"]
            assert "Invalid booking details" in result["user_friendly_error"]
    
    def test_schedule_meeting_unauthorized(self, mock_env, mock_api_key, booking_params):
        """Test handling of 401 Unauthorized"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert result["status_code"] == 401
            assert "Authentication failed" in result["user_friendly_error"]
    
    def test_schedule_meeting_not_found(self, mock_env, mock_api_key, booking_params):
        """Test handling of 404 Not Found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Calendar not found"}
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert result["status_code"] == 404
            assert "Calendar 'BKC-TEST123' not found" in result["user_friendly_error"]
    
    def test_schedule_meeting_server_error(self, mock_env, mock_api_key, booking_params):
        """Test handling of 500 Server Error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal server error"}
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert result["status_code"] == 500
            assert "Server error occurred" in result["user_friendly_error"]
    
    def test_schedule_meeting_timeout(self, mock_env, mock_api_key, booking_params):
        """Test handling of timeout"""
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            result = schedule_meeting(**booking_params, timeout=5)
            
            assert result["success"] is False
            assert "timed out after 5 seconds" in result["error"]
            assert "booking request timed out" in result["user_friendly_error"]
    
    def test_schedule_meeting_request_error(self, mock_env, mock_api_key, booking_params):
        """Test handling of request errors"""
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.RequestError("Connection failed")
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is False
            assert "Request failed" in result["error"]
            assert "Failed to connect" in result["user_friendly_error"]
    
    def test_schedule_meeting_invalid_json_response(self, mock_env, mock_api_key, booking_params):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Not a JSON response"
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = schedule_meeting(**booking_params)
            
            assert result["success"] is True  # Still success status code
            assert "Response is not valid JSON" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
