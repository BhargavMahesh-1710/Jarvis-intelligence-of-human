"""
Data Models for Android Phone Agent Integration.
Conforms to Section 4 of the Architecture Blueprint.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time

class PhoneActionRequest(BaseModel):
    action: str
    contact: Optional[str] = None
    message: Optional[str] = None
    phone_number: Optional[str] = None
    app_name: Optional[str] = None
    confirmation_required: bool = False

class PhoneActionResponse(BaseModel):
    success: bool
    action: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class PhoneEvent(BaseModel):
    event_type: str  # INCOMING_CALL, SMS_RECEIVED, NOTIFICATION, BATTERY_LEVEL
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

class PhoneDeviceStatus(BaseModel):
    connected: bool = False
    device_model: str = "Unpaired Device"
    battery_percentage: int = 100
    is_charging: bool = False
    wifi_connected: bool = True
    last_seen: float = 0.0
