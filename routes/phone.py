"""
JARVIS Android Agent Companion API & WebSocket Routes.
Implements Section 4 & 9 of the Architecture Blueprint.
Provides control over paired Android device capabilities (Calls, SMS, Notifications, Status).
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from agents.android.gateway import android_gateway
from agents.android.models import (
    PhoneActionRequest,
    PhoneActionResponse,
    PhoneEvent,
    PhoneDeviceStatus
)

logger = logging.getLogger("jarvis.routes.phone")

router = APIRouter(prefix="/api/phone", tags=["phone"])

class CallRequest(BaseModel):
    contact: str

class SMSRequest(BaseModel):
    contact: str
    message: str

class StatusUpdateRequest(BaseModel):
    connected: bool = True
    battery_percentage: int = 100
    is_charging: bool = False
    device_model: Optional[str] = None

@router.get("/status", response_model=PhoneDeviceStatus)
def get_phone_status():
    """Returns battery, connection status, and device metadata for paired Android agent."""
    return android_gateway.status

@router.post("/status", response_model=PhoneDeviceStatus)
def update_phone_status(req: StatusUpdateRequest):
    """Allows companion phone to update its battery and connectivity status."""
    android_gateway.status.connected = req.connected
    android_gateway.status.battery_percentage = req.battery_percentage
    android_gateway.status.is_charging = req.is_charging
    if req.device_model:
        android_gateway.status.device_model = req.device_model
    return android_gateway.status

@router.post("/call", response_model=PhoneActionResponse)
def place_phone_call(req: CallRequest):
    """Initiates a cellular phone call via the Android companion."""
    action_req = PhoneActionRequest(action="call_contact", contact=req.contact)
    return android_gateway.execute_phone_action(action_req)

@router.post("/sms", response_model=PhoneActionResponse)
def send_phone_sms(req: SMSRequest):
    """Sends an SMS text message to the specified contact."""
    action_req = PhoneActionRequest(action="send_sms", contact=req.contact, message=req.message)
    return android_gateway.execute_phone_action(action_req)

@router.get("/pairing-info")
def get_pairing_info():
    """Returns local network IP, mobile companion URL, and instructions for Vivo T4."""
    return android_gateway.get_pairing_info()

class SetDeviceRequest(BaseModel):
    model: str = "Vivo T4"
    battery: Optional[int] = None
    charging: Optional[bool] = None

@router.post("/set-device")
def set_device_profile(req: SetDeviceRequest):
    """Sets the active device profile to the user's specific phone (e.g. Vivo T4)."""
    android_gateway.set_device_profile(model=req.model, battery=req.battery, charging=req.charging)
    return {"success": True, "device": req.model, "status": android_gateway.status}

@router.post("/event")
def receive_phone_event(event: PhoneEvent):
    """Receives inbound push events from Android (Incoming call, Notification, Battery alert)."""
    android_gateway.handle_incoming_event(event)
    return {"success": True, "message": "Event processed"}

@router.websocket("/ws")
async def phone_companion_websocket(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket stream for the physical Android companion app.
    Streams directives to the phone and listens for device events.
    """
    await websocket.accept()
    logger.info("Physical Android device connected to /api/phone/ws")
    try:
        while True:
            data = await websocket.receive_json()
            if "event_type" in data:
                event = PhoneEvent(**data)
                android_gateway.handle_incoming_event(event)
    except WebSocketDisconnect:
        logger.info("Android device disconnected")
    except Exception as e:
        logger.warning(f"Android companion socket error: {e}")
