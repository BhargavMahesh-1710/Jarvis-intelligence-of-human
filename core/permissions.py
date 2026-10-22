"""
JARVIS 3-Tier Permission & Safety Gatekeeper.
Implements Section 12 & 14 (Rule 4, 5, 11) of the Architecture Blueprint.
Enforces server-side validation:
- LOW: Automatic execution
- MEDIUM: Interactive confirmation required
- HIGH: Strong explicit approval required
"""

import uuid
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from tools.base import ToolRiskLevel

class PendingAuthorization(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    description: str
    risk_level: ToolRiskLevel
    created_at: float = Field(default_factory=time.time)
    expires_at: float = Field(default_factory=lambda: time.time() + 180)  # 3 minute expiry

class PermissionGatekeeper:
    """
    Server-side gatekeeper that evaluates and holds pending actions
    based on risk level. The LLM can never bypass this layer.
    """
    def __init__(self):
        self._pending_actions: Dict[str, PendingAuthorization] = {}

    def evaluate_risk(self, tool_name: str, arguments: Dict[str, Any], declared_risk: ToolRiskLevel) -> ToolRiskLevel:
        """
        Dynamically adjusts or verifies the risk level.
        Even if a tool claims 'low', certain parameters (e.g. destructive file deletions)
        are escalated to MEDIUM or HIGH.
        """
        t = tool_name.lower()
        if "delete" in t or "remove" in t or "format" in t or "purge" in t:
            return ToolRiskLevel.MEDIUM
        if "pay" in t or "buy" in t or "purchase" in t or "transfer" in t:
            return ToolRiskLevel.HIGH
        if "phone.send_sms" in t or "phone.call_contact" in t:
            return ToolRiskLevel.MEDIUM
        return declared_risk

    def requires_confirmation(self, risk_level: ToolRiskLevel) -> bool:
        """Determines if user confirmation is required before execution."""
        return risk_level in (ToolRiskLevel.MEDIUM, ToolRiskLevel.HIGH)

    def create_authorization_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        description: str,
        risk_level: ToolRiskLevel
    ) -> PendingAuthorization:
        """Creates and stores a pending authorization request."""
        # Cleanup expired requests
        now = time.time()
        self._pending_actions = {k: v for k, v in self._pending_actions.items() if v.expires_at > now}

        pending = PendingAuthorization(
            tool_name=tool_name,
            arguments=arguments,
            description=description,
            risk_level=risk_level
        )
        self._pending_actions[pending.action_id] = pending
        return pending

    def resolve_authorization(self, action_id: str, approved: bool) -> Optional[PendingAuthorization]:
        """Resolves an authorization request."""
        now = time.time()
        pending = self._pending_actions.pop(action_id, None)
        if not pending or pending.expires_at <= now:
            return None
        return pending if approved else None

    def get_pending(self, action_id: str) -> Optional[PendingAuthorization]:
        """Retrieves a pending authorization without removing it."""
        return self._pending_actions.get(action_id)

    def get_latest_pending(self) -> Optional[PendingAuthorization]:
        """Retrieves the most recent unexpired pending authorization."""
        now = time.time()
        valid = [v for v in self._pending_actions.values() if v.expires_at > now]
        if valid:
            valid.sort(key=lambda x: x.created_at, reverse=True)
            return valid[0]
        return None

    def list_pending(self) -> Dict[str, PendingAuthorization]:
        """Returns all unexpired pending authorizations."""
        now = time.time()
        return {k: v for k, v in self._pending_actions.items() if v.expires_at > now}

permission_gatekeeper = PermissionGatekeeper()
