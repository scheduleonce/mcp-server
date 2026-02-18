from pydantic import BaseModel, Field
from typing import Optional, List


class Location(BaseModel):
    """Model representing a meeting location."""
    type: str = Field(..., description="Type of location (physical, virtual, phone)")
    value: str = Field(..., description="Location details (address, URL, phone number)")
    
    def to_dict(self):
        """Convert to dictionary for API requests."""
        return {
            "type": self.type,
            "value": self.value
        }
