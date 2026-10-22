import uuid
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# List of actions or tool verbs considered consequential
CONSEQUENTIAL_TOOLS = {
    "delete_file",
    "write_file",
    "execute_system_command",
    "send_email",
    "purchase",
    "clear_memory"
}

@dataclass
class PendingAction:
    action_id: str
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    created_at: float
    status: str = "pending"  # pending, approved, rejected, executed

class SafetyManager:
    def __init__(self):
        self._pending_actions: Dict[str, PendingAction] = {}
        self._audit_log: list = []

    def is_consequential(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> bool:
        """Determines if an action requires explicit user confirmation."""
        if tool_name in CONSEQUENTIAL_TOOLS:
            return True
        # Specific argument checks (e.g. overwriting/deleting)
        if tool_name == "files" and arguments:
            action = arguments.get("action", "").lower()
            if action in ["delete", "remove", "overwrite", "write"]:
                return True
        return False

    def create_pending_action(self, tool_name: str, arguments: Dict[str, Any], description: str) -> PendingAction:
        action_id = str(uuid.uuid4())[:8]
        pending = PendingAction(
            action_id=action_id,
            tool_name=tool_name,
            arguments=arguments,
            description=description,
            created_at=time.time(),
            status="pending"
        )
        self._pending_actions[action_id] = pending
        self.log_event(
            tool_name=tool_name,
            arguments=arguments,
            status="awaiting_confirmation",
            details=f"Action paused for user approval: {description}",
            is_consequential=True
        )
        return pending

    def get_pending_action(self, action_id: str) -> Optional[PendingAction]:
        return self._pending_actions.get(action_id)

    def resolve_action(self, action_id: str, approved: bool) -> Optional[PendingAction]:
        action = self._pending_actions.get(action_id)
        if not action:
            return None
        action.status = "approved" if approved else "rejected"
        self.log_event(
            tool_name=action.tool_name,
            arguments=action.arguments,
            status="approved" if approved else "rejected_by_user",
            details=f"User {'approved' if approved else 'rejected'} action {action_id}",
            is_consequential=True
        )
        return action

    def log_event(self, tool_name: str, arguments: Dict[str, Any], status: str, details: Any, is_consequential: bool):
        entry = {
            "timestamp": time.time(),
            "tool_name": tool_name,
            "arguments": arguments,
            "status": status,
            "details": str(details),
            "is_consequential": is_consequential
        }
        self._audit_log.append(entry)

    def get_audit_log(self, limit: int = 50) -> list:
        return self._audit_log[-limit:]

safety_manager = SafetyManager()
