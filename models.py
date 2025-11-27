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


class BookingForm(BaseModel):
    """Model representing a booking form with guest information."""
    name: str = Field(..., description="Guest's full name")
    email: str = Field(..., description="Guest's email address")
    phone: Optional[str] = Field(default=None, description="Guest's phone number")
    string_custom_fields: str = Field(default="", description="Custom string fields")
    array_custom_fields: List[str] = Field(default_factory=list, description="Custom array fields")
    
    def to_dict(self):
        """Convert to dictionary for API requests."""
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "string_custom_fields": self.string_custom_fields,
            "array_custom_fields": self.array_custom_fields
        }
