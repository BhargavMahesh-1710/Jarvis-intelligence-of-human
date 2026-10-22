"""
JARVIS Context Manager.
Implements Section 1 & 2 of the Architecture Blueprint.
Maintains state across:
1. Current Task Context (goal, steps, active tool)
2. Conversation Context (recent turns)
3. Environment Context (OS, active window, network, paired phone status)
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TaskContext(BaseModel):
    task_id: str = ""
    goal: str = ""
    plan_steps: List[Dict[str, Any]] = Field(default_factory=list)
    current_step_index: int = 0
    status: str = "idle"  # idle, planning, executing, verifying, completed, failed
    last_error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)

class EnvironmentContext(BaseModel):
    os_name: str = "Windows"
    is_web_ui: bool = True
    volume_level: Optional[int] = None
    muted: bool = False
    phone_connected: bool = False
    phone_battery: Optional[int] = None
    active_app: Optional[str] = None

class ContextManager:
    """
    Central context manager for the JARVIS AI Brain.
    """
    def __init__(self):
        self.task = TaskContext()
        self.environment = EnvironmentContext()
        self._conversation_history: List[Dict[str, str]] = []
        self._max_history: int = 15

    def start_task(self, task_id: str, goal: str, plan_steps: Optional[List[Dict[str, Any]]] = None) -> None:
        """Initializes context for a new task."""
        self.task = TaskContext(
            task_id=task_id,
            goal=goal,
            plan_steps=plan_steps or [],
            current_step_index=0,
            status="executing"
        )

    def update_task_status(self, status: str, error: Optional[str] = None) -> None:
        """Updates the status of the current task."""
        self.task.status = status
        if error:
            self.task.last_error = error

    def finish_task(self) -> None:
        """Resets task context upon completion."""
        self.task = TaskContext()

    def record_interaction(self, role: str, content: str) -> None:
        """Maintains conversation memory sliding window."""
        self._conversation_history.append({"role": role, "content": content})
        if len(self._conversation_history) > self._max_history:
            self._conversation_history.pop(0)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Returns recent conversation history."""
        return list(self._conversation_history)

    def get_full_context_summary(self) -> str:
        """Generates a structured prompt injection summary for the LLM."""
        lines = []
        if self.task.goal:
            lines.append(f"Active Task: {self.task.goal} (Status: {self.task.status})")
        lines.append(f"Environment: {self.environment.os_name} | Phone Connected: {self.environment.phone_connected}")
        return "\n".join(lines)

context_manager = ContextManager()
