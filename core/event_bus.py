"""
JARVIS Real-Time WebSocket Event Bus.
Implements Section 11 of the Architecture Blueprint.
Decouples HUD visual animations & telemetry from the core AI reasoning loop.
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("jarvis.core.event_bus")

class EventType:
    THINKING = "THINKING"
    TOOL_ROUTED = "TOOL_ROUTED"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    TOOL_VERIFYING = "TOOL_VERIFYING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    GESTURE_DETECTED = "GESTURE_DETECTED"
    STATUS_UPDATE = "STATUS_UPDATE"

class EventBus:
    """
    Asynchronous event broadcaster.
    Publishes real-time telemetry to all connected WebSocket clients (HUD / Telemetry displays).
    """
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Sets the main asyncio loop for cross-thread event forwarding."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        """Registers a new WebSocket client connection."""
        await websocket.accept()
        self._active_connections.add(websocket)
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        logger.info(f"Client connected to EventBus. Total clients: {len(self._active_connections)}")
        # Send initial handshake event
        await self.publish(EventType.STATUS_UPDATE, {
            "message": "Connected to JARVIS Neural Event Bus",
            "active_clients": len(self._active_connections)
        })

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        self._active_connections.discard(websocket)
        logger.info(f"Client disconnected from EventBus. Remaining: {len(self._active_connections)}")

    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Publishes a typed event to all active WebSocket listeners.
        """
        payload = {
            "event": event_type,
            "timestamp": time.time(),
            **(data or {})
        }
        json_str = json.dumps(payload)

        # Broadcast to all connections; prune stale connections
        dead_connections = set()
        for connection in list(self._active_connections):
            try:
                await connection.send_text(json_str)
            except Exception:
                dead_connections.add(connection)

        for dead in dead_connections:
            self._active_connections.discard(dead)

    def publish_sync(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Synchronous wrapper to safely publish events from synchronous code or background worker threads.
        """
        # 1. Try forwarding to main loop if from another thread
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.publish(event_type, data), self._loop)
                return
            except Exception as e:
                logger.debug(f"threadsafe dispatch failed: {e}")

        # 2. Check if current thread has a running loop
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event_type, data))
                return
            else:
                loop.run_until_complete(self.publish(event_type, data))
                return
        except RuntimeError:
            pass

        # 3. Fallback standalone loop
        try:
            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(self.publish(event_type, data))
            new_loop.close()
        except Exception as e:
            logger.warning(f"Failed to publish sync event: {e}")

# Global Event Bus Singleton
event_bus = EventBus()
