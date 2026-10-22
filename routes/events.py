"""
JARVIS Real-Time WebSocket Event Stream & Telemetry Router.
Implements Section 11 of the Architecture Blueprint.
Streams orchestrator states, tool routing, execution results, safety alerts, and hand gestures to HUD.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.event_bus import event_bus
from tools.registry import tool_registry

logger = logging.getLogger("jarvis.routes.events")

router = APIRouter(tags=["events"])

@router.websocket("/ws/events")
async def websocket_event_stream(websocket: WebSocket):
    """
    Subscribes the Holographic HUD to real-time events:
    THINKING, TOOL_ROUTED, TOOL_EXECUTION, TOOL_VERIFYING, SUCCESS, ERROR, CONFIRMATION_REQUIRED, GESTURE_DETECTED.
    """
    await event_bus.connect(websocket)
    try:
        while True:
            # Keep alive & listen for client ping or incoming actions
            client_msg = await websocket.receive_text()
            logger.debug(f"Received client event ping: {client_msg}")
    except WebSocketDisconnect:
        event_bus.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket closed: {e}")
        event_bus.disconnect(websocket)

@router.get("/api/tools")
def list_registered_tools() -> List[Dict[str, Any]]:
    """
    Returns introspection metadata for all registered tools in the platform:
    names, risk levels, categories, parameters, and descriptions.
    """
    schemas = tool_registry.get_schemas()
    return schemas
