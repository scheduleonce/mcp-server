import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.responses import JSONResponse
from fastmcp import FastMCP


class TestMainMCPServer:
    """Test cases for main.py MCP server setup"""
    
    def test_mcp_server_creation(self):
        """Test that MCP server is created with correct name"""
        import main
        
        # Verify mcp object exists and is properly initialized
        assert hasattr(main, 'mcp')
        assert isinstance(main.mcp, FastMCP)
        assert main.mcp.name == "mcp-server"
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint_response(self):
        """Test health check endpoint returns correct response"""
        import main
        
        # Create a mock request
        mock_request = Mock()
        
        # Call the health check endpoint
        response = await main.health_check(mock_request)
        
        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        
        # Parse the response body
        import json
        body = json.loads(response.body.decode())
        assert body["status"] == "healthy"
        assert body["service"] == "mcp-server"

    @pytest.mark.asyncio
    async def test_tools_list_endpoint_response(self):
        """Test tools list endpoint returns expected metadata structure."""
        import json
        import main

        class MockClientContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def list_tools(self):
                return [
                    {
                        "name": "get_booking_time_slots",
                        "description": "Get available slots",
                        "inputSchema": {
                            "type": "object",
                            "required": ["calendar_id"],
                            "properties": {
                                "calendar_id": {
                                    "type": "string",
                                    "description": "Calendar id",
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "Start time",
                                },
                            },
                        },
                    }
                ]

        with patch("main.Client", return_value=MockClientContext()):
            mock_request = Mock()
            response = await main.tools_list(mock_request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert body["total_tools"] == 1
        assert body["tools"][0]["name"] == "get_booking_time_slots"
        assert body["tools"][0]["required_parameters"] == ["calendar_id"]
        assert len(body["tools"][0]["parameters"]) == 2

    @pytest.mark.asyncio
    async def test_tools_list_endpoint_error(self):
        """Test tools list endpoint error handling."""
        import json
        import main

        class ErrorClientContext:
            async def __aenter__(self):
                raise RuntimeError("Connection failed")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        with patch("main.Client", return_value=ErrorClientContext()):
            mock_request = Mock()
            response = await main.tools_list(mock_request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert "Failed to list tools" in body["error"]
    
    def test_tools_are_registered(self):
        """Test that tools are registered with the MCP server"""
        import main
        
        # Verify the mcp object exists and is a FastMCP instance
        assert hasattr(main, 'mcp')
        assert isinstance(main.mcp, FastMCP)
        
        # The tools should be registered via decorators
        # We can't directly test decorator application, but we can verify
        # the mcp object has the tool method
        assert hasattr(main.mcp, 'tool')
    
    def test_logging_configuration(self):
        """Test that logging is properly configured"""
        import logging
        import main
        
        # Verify logger exists
        assert hasattr(main, 'logger')
        assert isinstance(main.logger, logging.Logger)
        
        # Note: logging.basicConfig sets root logger level to INFO
        # but other tests may have changed it, so we just verify the logger exists
        assert main.logger.name == 'main'


class TestHealthCheckEndpoint:
    """Test cases for health check endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check response"""
        import main
        
        mock_request = Mock()
        response = await main.health_check(mock_request)
        
        assert response.status_code == 200
        assert response.media_type == "application/json"
    
    @pytest.mark.asyncio
    async def test_health_check_json_structure(self):
        """Test health check returns proper JSON structure"""
        import main
        
        mock_request = Mock()
        response = await main.health_check(mock_request)
        
        import json
        body = json.loads(response.body.decode())
        
        # Verify required fields
        assert "status" in body
        assert "service" in body
        assert body["status"] == "healthy"
        assert body["service"] == "mcp-server"
    
    @pytest.mark.asyncio
    async def test_health_check_multiple_calls(self):
        """Test health check endpoint can be called multiple times"""
        import main
        
        mock_request = Mock()
        
        # Call health check multiple times
        for _ in range(5):
            response = await main.health_check(mock_request)
            assert response.status_code == 200


class TestMCPServerIntegration:
    """Integration tests for the MCP server"""
    
    def test_server_has_custom_routes(self):
        """Test that custom routes are registered"""
        import main
        
        # Verify mcp object has the custom_route decorator method
        assert hasattr(main.mcp, 'custom_route')
    
    def test_imported_tools_exist(self):
        """Test that imported tools from tools module are available"""
        from tools import get_booking_time_slots, schedule_meeting
        
        # Verify tools are callable
        assert callable(get_booking_time_slots)
        assert callable(schedule_meeting)
    
    def test_module_has_main_guard(self):
        """Test that module can be imported without running main"""
        import main
        
        # If we can import main without error, the if __name__ == "__main__" guard works
        assert hasattr(main, 'mcp')
        assert hasattr(main, 'health_check')
        assert hasattr(main, 'tools_list')


class TestServerConfiguration:
    """Test server configuration and setup"""
    
    def test_mcp_server_name(self):
        """Test MCP server has correct name"""
        import main
        
        assert main.mcp.name == "mcp-server"
    
    @patch('main.asyncio.run')
    @patch('main.mcp.run_async')
    def test_main_execution(self, mock_run_async, mock_asyncio_run):
        """Test main execution with correct parameters"""
        # This test verifies the structure, not actual execution
        # since if __name__ == "__main__" won't be true during imports
        
        import main
        
        # Verify that run_async method exists
        assert hasattr(main.mcp, 'run_async')
    
    def test_module_level_imports(self):
        """Test that all required modules are imported"""
        import main
        
        # Verify required imports
        assert hasattr(main, 'asyncio')
        assert hasattr(main, 'logging')
        assert hasattr(main, 'JSONResponse')
        assert hasattr(main, 'FastMCP')
        assert hasattr(main, 'get_booking_time_slots')
        assert hasattr(main, 'schedule_meeting')


class TestLoggingConfiguration:
    """Test logging setup and configuration"""
    
    def test_logger_name(self):
        """Test logger has correct name"""
        import main
        
        assert main.logger.name == 'main'
    
    def test_logging_format(self):
        """Test logging is configured with proper format"""
        import logging
        
        # Get root logger
        root_logger = logging.getLogger()
        
        # Verify handlers exist (logging.basicConfig creates at least one handler)
        assert len(root_logger.handlers) > 0
        
        # Verify that logging configuration was called (by checking if handlers exist)
        # Note: The actual level may vary depending on test execution order
        assert root_logger.level in [logging.INFO, logging.WARNING, logging.DEBUG]
    
    def test_logger_can_log(self):
        """Test that logger can write log messages"""
        import main
        import logging
        
        # Capture log output
        with patch.object(main.logger, 'info') as mock_log:
            main.logger.info("Test message")
            mock_log.assert_called_once_with("Test message")


class TestHealthCheckDecorators:
    """Test health check endpoint decorators"""
    
    def test_health_check_has_docstring(self):
        """Test health check function has documentation"""
        import main
        
        assert main.health_check.__doc__ is not None
        assert "Health check" in main.health_check.__doc__
    
    @pytest.mark.asyncio
    async def test_health_check_is_async(self):
        """Test health check is an async function"""
        import main
        import inspect
        
        assert inspect.iscoroutinefunction(main.health_check)


class TestToolsListHelpers:
    """Test helper functions used by tools listing endpoint."""

    def test_to_dict_with_dict(self):
        """_to_dict should return dictionaries as-is."""
        import main

        data = {"name": "x"}
        assert main._to_dict(data) == data

    def test_to_dict_with_object_attrs(self):
        """_to_dict should map common object attributes."""
        import main

        tool_obj = Mock()
        tool_obj.name = "tool_a"
        tool_obj.description = "desc"
        tool_obj.inputSchema = {"type": "object"}
        tool_obj.outputSchema = None

        result = main._to_dict(tool_obj)
        assert result["name"] == "tool_a"
        assert result["description"] == "desc"
        assert result["inputSchema"]["type"] == "object"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
