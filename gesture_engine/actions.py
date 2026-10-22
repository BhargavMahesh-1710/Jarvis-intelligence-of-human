"""
Gesture Action Dispatcher for JARVIS.
Dispatches normalized gesture intents into system control actions.
"""

import time
import logging
from typing import Dict, Any, Optional
from core.event_bus import event_bus, EventType
from core.permissions import permission_gatekeeper
from tools.device_control import control_volume

logger = logging.getLogger("jarvis.gesture_engine.actions")

class GestureActionDispatcher:
    """
    Executes system actions in response to detected hand gestures.
    Includes debounce tracking to prevent multiple rapid triggers.
    """
    def __init__(self):
        self._last_gesture = ""
        self._last_trigger_time = 0
        self._debounce_seconds = 1.2
        self._last_volume_time = 0

    def dispatch(self, gesture_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = time.time()
        gesture_name = gesture_data.get("gesture", "")
        intent = gesture_data.get("intent", "")

        # Volume control can trigger faster for smooth continuous adjustment
        if intent == "VOLUME_CONTROL":
            if now - self._last_volume_time < 0.25:
                return None
            self._last_volume_time = now
            val = gesture_data.get("value", 50)
            # If pinch is close, step volume up or down
            direction = "up" if val > 50 else "down"
            control_volume(direction)
            event_bus.publish_sync(EventType.GESTURE_DETECTED, {
                "gesture": "PINCH",
                "action": f"VOLUME_{direction.upper()}",
                "value": val
            })
            return {"action": f"volume_{direction}", "value": val}

        # For discrete gestures (CONFIRM, CANCEL, PAUSE, NEXT), apply debounce
        if gesture_name == self._last_gesture and (now - self._last_trigger_time) < self._debounce_seconds:
            return None

        self._last_gesture = gesture_name
        self._last_trigger_time = now

        logger.info(f"Gesture detected & dispatched: {gesture_name} -> {intent}")

        # Broadcast event to HUD
        event_bus.publish_sync(EventType.GESTURE_DETECTED, {
            "gesture": gesture_name,
            "intent": intent
        })

        if intent == "CONFIRM":
            # Check if there is any pending security action and approve it!
            # Thumbs up directly authorizes consequential actions!
            pending = permission_gatekeeper.get_latest_pending()
            if pending:
                permission_gatekeeper.resolve_authorization(pending.action_id, approved=True)
                from tools.registry import tool_registry
                res = tool_registry.execute(pending.tool_name, pending.arguments)
                event_bus.publish_sync(EventType.SUCCESS, {
                    "tool": pending.tool_name,
                    "message": f"Action '{pending.tool_name}' authorized and executed via Thumbs Up 👍",
                    "output": res.output
                })
                logger.info(f"Gesture CONFIRM approved and executed pending action: {pending.tool_name}")
                return {"action": "confirm_authorization", "status": "approved", "tool": pending.tool_name}
            return {"action": "confirm_authorization", "status": "no_pending"}

        elif intent == "CANCEL":
            # Thumbs down rejects
            pending = permission_gatekeeper.get_latest_pending()
            if pending:
                permission_gatekeeper.resolve_authorization(pending.action_id, approved=False)
                event_bus.publish_sync(EventType.STATUS_UPDATE, {
                    "message": f"Action '{pending.tool_name}' rejected and cancelled via Thumbs Down 👎"
                })
                logger.info(f"Gesture CANCEL rejected pending action: {pending.tool_name}")
                return {"action": "cancel_authorization", "status": "rejected", "tool": pending.tool_name}
            return {"action": "cancel_authorization", "status": "no_pending"}

        elif intent == "PAUSE":
            event_bus.publish_sync(EventType.STATUS_UPDATE, {
                "message": "Operations paused via Open Palm gesture ✋"
            })
            return {"action": "pause_operations", "status": "paused"}

        elif intent == "NEXT":
            event_bus.publish_sync(EventType.STATUS_UPDATE, {
                "message": "Next track / page triggered via Two Fingers gesture ✌️"
            })
            return {"action": "next_item", "status": "triggered"}

        return None

gesture_dispatcher = GestureActionDispatcher()
