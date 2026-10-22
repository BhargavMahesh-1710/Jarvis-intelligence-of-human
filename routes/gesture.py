"""
JARVIS Gesture Engine Control Router.
Implements Section 5 of the Architecture Blueprint.
Controls the background MediaPipe/OpenCV gesture recognition service and allows gesture simulation.
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter
from gesture_engine.detector import gesture_detector
from gesture_engine.actions import gesture_dispatcher
from core.event_bus import event_bus, EventType

logger = logging.getLogger("jarvis.routes.gesture")

router = APIRouter(prefix="/api/gesture", tags=["gesture"])

class SimulateGestureRequest(BaseModel):
    gesture: str  # PINCH, OPEN_PALM, THUMBS_UP, THUMBS_DOWN, INDEX_FINGER, TWO_FINGERS
    intent: Optional[str] = None
    value: Optional[float] = None

@router.get("/status")
def get_gesture_status():
    """Returns whether the real-time webcam gesture detector is active."""
    return {
        "active": gesture_detector.is_active(),
        "camera_available": True
    }

@router.post("/start")
def start_gesture_detector(camera_index: int = 0):
    """Starts the real-time background webcam gesture detector thread."""
    success = gesture_detector.start(camera_index=camera_index)
    event_bus.publish_sync(EventType.STATUS_UPDATE, {
        "message": f"🖐️ Gesture Recognition Engine {'ONLINE' if success else 'FAILED TO START'}"
    })
    return {
        "success": success,
        "active": gesture_detector.is_active(),
        "message": "Gesture detector started" if success else "Failed to open camera"
    }

@router.post("/stop")
def stop_gesture_detector():
    """Stops the real-time background webcam gesture detector and releases camera hardware."""
    gesture_detector.stop()
    event_bus.publish_sync(EventType.STATUS_UPDATE, {
        "message": "🖐️ Gesture Recognition Engine OFFLINE (Hardware released)"
    })
    return {
        "success": True,
        "active": False,
        "message": "Gesture detector stopped"
    }

@router.post("/simulate")
def simulate_gesture(req: SimulateGestureRequest):
    """
    Simulates a detected gesture without requiring physical camera input.
    Useful for testing, automated verification, or frontend quick triggers.
    """
    g = req.gesture.upper()
    intent_map = {
        "PINCH": "VOLUME_CONTROL",
        "THUMBS_UP": "CONFIRM",
        "THUMBS_DOWN": "CANCEL",
        "OPEN_PALM": "PAUSE",
        "TWO_FINGERS": "NEXT",
        "INDEX_FINGER": "POINT"
    }
    intent = req.intent or intent_map.get(g, "UNKNOWN")
    gesture_data = {
        "gesture": g,
        "intent": intent,
        "confidence": 0.99,
        "value": req.value if req.value is not None else 50.0
    }
    result = gesture_dispatcher.dispatch(gesture_data)
    return {
        "success": True,
        "simulated": gesture_data,
        "action_result": result
    }
