"""
Universal JARVIS Execution Orchestrator.
Faithfully implements the 11-Step Algorithm from Section 2 & 14 of the Architecture Specification.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.event_bus import event_bus, EventType
from core.context import context_manager
from core.permissions import permission_gatekeeper
from core.memory import memory_store
from tools.registry import tool_registry
from tools.base import ToolResult, ToolRiskLevel
from core.agent import normalize_command

logger = logging.getLogger("jarvis.core.orchestrator")

class ExecutionResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    plan: List[str] = Field(default_factory=list)
    pending_action: Optional[Dict[str, Any]] = None
    open_url: Optional[str] = None
    action_type: Optional[str] = None
    target: Optional[str] = None
    folder_path: Optional[str] = None
    folder_name: Optional[str] = None
    files: Optional[List[Dict[str, Any]]] = None
    file_url: Optional[str] = None
    is_image: Optional[bool] = None
    path: Optional[str] = None
    embed_url: Optional[str] = None
    video_id: Optional[str] = None
    action: Optional[str] = None
    aux_display: Optional[Dict[str, Any]] = None
    verified: bool = False

class UniversalOrchestrator:
    """
    Executes the 11-Step Universal JARVIS Algorithm:
    1. Receive input
    2. Understand
    3. Classify
    4. Plan
    5. Authorize
    6. Execute
    7. Observe
    8. Verify
    9. Recover
    10. Respond
    11. Remember
    """
    def __init__(self):
        self.user_name = "Mahi"

    def process(self, raw_input: str, user_name: str = "Mahi") -> ExecutionResponse:
        self.user_name = user_name
        start_time = time.time()

        # Step 1: Receive input
        event_bus.publish_sync(EventType.THINKING, {
            "message": f"Analyzing directive: '{raw_input[:60]}...'",
            "raw_input": raw_input
        })

        # Step 2: Understand (Normalize & extract entities)
        normalized = normalize_command(raw_input)
        context_manager.record_interaction("user", raw_input)

        norm_lower = normalized.lower().strip()
        # Immediate check for pending safety authorization confirmation / cancellation
        pending = permission_gatekeeper.get_latest_pending()
        if pending:
            affirmative = ["confirm", "approve", "authorize", "yes", "proceed", "yes proceed", "yes do it", "sure", "authorized", "do it", "ok", "okay"]
            negative = ["cancel", "deny", "reject", "no", "no cancel", "abort", "disapprove", "don't do it", "stop"]
            if any(norm_lower == a or norm_lower.startswith(f"{a} ") or norm_lower.endswith(f" {a}") for a in affirmative):
                permission_gatekeeper.resolve_authorization(pending.action_id, approved=True)
                event_bus.publish_sync(EventType.TOOL_EXECUTION, {"tool": pending.tool_name, "arguments": pending.arguments})
                res = tool_registry.execute(pending.tool_name, pending.arguments)
                event_bus.publish_sync(EventType.SUCCESS, {"tool": pending.tool_name, "verified": True})
                return ExecutionResponse(
                    reply=f"Action '{pending.tool_name}' authorized and executed successfully: {res.message}",
                    intent="confirmation",
                    tools_used=[pending.tool_name],
                    verified=True
                )
            if any(norm_lower == n or norm_lower.startswith(f"{n} ") or norm_lower.endswith(f" {n}") for n in negative):
                permission_gatekeeper.resolve_authorization(pending.action_id, approved=False)
                event_bus.publish_sync(EventType.STATUS_UPDATE, {"message": f"Action '{pending.tool_name}' cancelled by user."})
                return ExecutionResponse(
                    reply=f"Action '{pending.tool_name}' has been cancelled as requested.",
                    intent="cancellation"
                )

        # Step 3: Classify (Determine task type, tool, and risk level)
        tool_call = self._classify_to_tool_call(normalized, raw_input)
        tool_name = tool_call["tool"]
        tool_args = tool_call["arguments"]
        intent_name = tool_call.get("intent", "general")

        event_bus.publish_sync(EventType.TOOL_ROUTED, {
            "tool": tool_name,
            "intent": intent_name,
            "arguments": tool_args
        })

        # Step 4: Plan (Create execution step plan)
        plan_desc = f"Execute tool '{tool_name}' with parameters {tool_args}"
        context_manager.start_task(
            task_id=f"task_{int(time.time())}",
            goal=raw_input,
            plan_steps=[{"tool": tool_name, "args": tool_args, "description": plan_desc}]
        )

        # Step 5: Authorize (Permission Layer Check)
        declared_risk = tool_registry.get_risk_level(tool_name)
        effective_risk = permission_gatekeeper.evaluate_risk(tool_name, tool_args, declared_risk)

        if permission_gatekeeper.requires_confirmation(effective_risk):
            pending = permission_gatekeeper.create_authorization_request(
                tool_name=tool_name,
                arguments=tool_args,
                description=f"Action '{tool_name}' requires confirmation.",
                risk_level=effective_risk
            )
            event_bus.publish_sync(EventType.CONFIRMATION_REQUIRED, {
                "action_id": pending.action_id,
                "tool": tool_name,
                "risk": effective_risk.value,
                "description": pending.description
            })
            return ExecutionResponse(
                reply=f"⚠️ Action '{tool_name}' classified as {effective_risk.value.upper()} risk. Awaiting your authorization.",
                intent=intent_name,
                tools_used=[tool_name],
                plan=[plan_desc],
                pending_action={
                    "action_id": pending.action_id,
                    "tool": pending.tool_name,
                    "description": pending.description,
                    "risk": effective_risk.value
                }
            )

        # Step 6: Execute
        event_bus.publish_sync(EventType.TOOL_EXECUTION, {
            "tool": tool_name,
            "arguments": tool_args
        })
        result: ToolResult = tool_registry.execute(tool_name, tool_args)

        # Step 7: Observe (Collect output)
        observed_output = result.output

        # Step 8: Verify (Check whether requested state was actually achieved)
        event_bus.publish_sync(EventType.TOOL_VERIFYING, {"tool": tool_name})
        is_verified = tool_registry.verify(tool_name, result, tool_args)
        result.verified = is_verified

        # Step 9: Recover (Handle failures gracefully)
        if not result.success:
            logger.warning(f"Tool {tool_name} failed. Attempting graceful recovery.")
            event_bus.publish_sync(EventType.ERROR, {"tool": tool_name, "error": result.error})
            # Fallback response
            reply_text = f"I encountered an issue executing {tool_name}: {result.error or 'Operation incomplete'}. How would you like me to proceed?"
        else:
            event_bus.publish_sync(EventType.SUCCESS, {
                "tool": tool_name,
                "verified": is_verified,
                "duration_ms": round((time.time() - start_time) * 1000, 1)
            })
            reply_text = result.message

        # Step 10: Respond (Assemble presentation data for HUD and Voice)
        meta = result.metadata or {}
        out_dict = result.output if isinstance(result.output, dict) else {}
        open_url_val = meta.get("open_url") or meta.get("url") or out_dict.get("open_url") or out_dict.get("url")
        embed_url_val = meta.get("embed_url") or out_dict.get("embed_url")
        video_id_val = meta.get("video_id") or out_dict.get("video_id")
        action_val = meta.get("action") or out_dict.get("action")
        aux_display_val = meta.get("aux_display") or out_dict.get("aux_display")

        resp = ExecutionResponse(
            reply=reply_text,
            intent=intent_name,
            tools_used=[tool_name],
            plan=[plan_desc],
            verified=is_verified,
            open_url=open_url_val,
            embed_url=embed_url_val,
            video_id=video_id_val,
            action=action_val,
            aux_display=aux_display_val
        )

        # Step 11: Remember (Extract valuable facts and commit)
        extracted = memory_store.extract_facts(raw_input)
        for fact in extracted:
            memory_store.save_memory(fact)

        context_manager.record_interaction("assistant", reply_text)
        context_manager.finish_task()
        return resp

    def _classify_to_tool_call(self, normalized: str, raw_input: str) -> Dict[str, Any]:
        """
        Maps normalized user input to a structured tool call.
        Conforms to Section 8 of the Architecture Specification.
        """
        t = normalized.lower().strip(" \t\r\n.,;:!?'\"`")

        # 1. Auxiliary Screen Commands
        if "display on screen" in t or "show on screen" in t or "show on aux screen" in t:
            text_to_show = raw_input
            for p in ["display on screen", "show on screen", "show on aux screen"]:
                if p in raw_input.lower():
                    idx = raw_input.lower().find(p) + len(p)
                    text_to_show = raw_input[idx:].strip(" :-\"'")
                    break
            return {
                "intent": "aux_screen",
                "tool": "aux_screen.display",
                "arguments": {"text": text_to_show}
            }

        if "screen mode" in t:
            mode = "feed"
            for m in ["matrix", "visualizer", "feed", "standby", "note"]:
                if m in t:
                    mode = m
                    break
            return {
                "intent": "aux_screen",
                "tool": "aux_screen.mode",
                "arguments": {"mode": mode}
            }

        # 2. YouTube & Music Playback
        if "youtube" in t or t.startswith("play ") or (("play" in t or "listen" in t) and ("song" in t or "music" in t or "video" in t or "track" in t)):
            import re
            query = re.sub(r"^(?:open\s+youtube\s+(?:and\s+)?play|play|listen\s+to)\s+", "", t).strip()
            query = re.sub(r"^(?:a|an|the|some)\s+", "", query).strip()
            query = re.sub(r"\s+(?:on\s+youtube|in\s+youtube|for\s+me|please)$", "", query).strip()
            return {
                "intent": "action",
                "tool": "media.play_youtube",
                "arguments": {"query": query or "trending music"}
            }

        # 3. Web Navigation & Searches
        if t.startswith("search ") or t.startswith("google ") or "search web" in t:
            q = t.replace("search web for", "").replace("search for", "").replace("search google for", "").replace("search", "").replace("google", "").strip()
            return {
                "intent": "search",
                "tool": "browser.search",
                "arguments": {"query": q or t}
            }

        # 4. Desktop Hardware & Apps (Open, Launch, Start, Run)
        is_open_cmd = any(t.startswith(prefix) for prefix in ["open ", "launch ", "start ", "run ", "open up ", "show me "])
        direct_apps = ["chrome", "google chrome", "notepad", "calculator", "calc", "paint", "cmd", "terminal", "powershell", "vscode", "vs code", "spotify", "task manager", "settings", "camera", "wifi", "bluetooth", "files", "explorer", "documents", "downloads", "desktop"]
        
        if is_open_cmd or t in direct_apps:
            import re
            app_target = re.sub(r"^(?:open\s+up|open|launch|start|run|show\s+me)\s+", "", t).strip(" \t\r\n.,;:!?'\"`")
            app_target = re.sub(r"^(?:the|my)\s+", "", app_target).strip(" \t\r\n.,;:!?'\"`")
            app_target = re.sub(r"\s+(?:for\s+me|please|app|application|program|software)$", "", app_target).strip(" \t\r\n.,;:!?'\"`")

            if any(app_target.startswith(k) for k in ["http://", "https://", "www."]) or app_target.endswith((".com", ".org", ".io", ".net", ".edu", ".in")):
                return {
                    "intent": "action",
                    "tool": "browser.open_site",
                    "arguments": {"site": app_target}
                }
            if app_target in ["youtube", "yt"]:
                return {
                    "intent": "action",
                    "tool": "media.play_youtube",
                    "arguments": {"query": "trending"}
                }
            return {
                "intent": "action",
                "tool": "computer.open_app",
                "arguments": {"app": app_target or t}
            }

        # Close Tab / Media directive (closes running tab or active YouTube playback and returns to JARVIS)
        close_tab_phrases = [
            "close it", "close this", "close tab", "close the tab", 
            "close this tab", "close current tab", "close the current tab",
            "close video", "close player", "stop video", "stop player",
            "return to jarvis", "back to jarvis", "close youtube", "close active tab"
        ]
        if any(w in t for w in close_tab_phrases) or t == "close":
            return {
                "intent": "action",
                "tool": "computer.window_control",
                "arguments": {"action": "close_tab"}
            }

        if any(t.startswith(prefix) for prefix in ["close ", "exit ", "kill ", "terminate ", "shut "]):
            import re
            app_target = re.sub(r"^(?:close|exit|kill|terminate|shut)\s+(?:down\s+)?", "", t).strip()
            app_target = re.sub(r"^(?:the|my)\s+", "", app_target).strip()
            app_target = re.sub(r"\s+(?:for\s+me|please|app|application|program|software)$", "", app_target).strip()
            return {
                "intent": "action",
                "tool": "computer.close_app",
                "arguments": {"app": app_target}
            }

        # 5. Hardware: Volume & Sound Controls
        import re
        m_vol_pct = re.search(r"\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\s*%?\b", t)
        if m_vol_pct:
            level = int(m_vol_pct.group(1))
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "set", "level": level}
            }
        if any(w in t for w in ["mute audio", "mute sound", "mute", "silence audio", "silence"]):
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "mute"}
            }
        if any(w in t for w in ["unmute audio", "unmute sound", "unmute"]):
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "unmute"}
            }
        if any(w in t for w in ["volume up", "increase volume", "raise volume", "louder", "turn up volume", "boost volume", "turn up sound"]):
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "up"}
            }
        if any(w in t for w in ["volume down", "decrease volume", "lower volume", "quieter", "turn down volume", "soften sound", "lower sound"]):
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "down"}
            }
        if any(w in t for w in ["max volume", "maximum volume", "full volume"]):
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "max", "level": 100}
            }
        if any(w in t for w in ["half volume", "50% volume"]):
            return {
                "intent": "action",
                "tool": "computer.volume",
                "arguments": {"action": "half", "level": 50}
            }

        # 6. Hardware: Screen Brightness Controls
        m_br_pct = re.search(r"\b(?:set\s+)?brightness\s+(?:to\s+)?(\d{1,3})\s*%?\b", t)
        if m_br_pct:
            level = int(m_br_pct.group(1))
            return {
                "intent": "action",
                "tool": "computer.brightness",
                "arguments": {"action": "set", "level": level}
            }
        if any(w in t for w in ["brightness up", "increase brightness", "screen brighter", "make screen brighter", "turn up brightness", "raise brightness"]):
            return {
                "intent": "action",
                "tool": "computer.brightness",
                "arguments": {"action": "up"}
            }
        if any(w in t for w in ["brightness down", "decrease brightness", "dim screen", "lower brightness", "turn down brightness", "dimmer"]):
            return {
                "intent": "action",
                "tool": "computer.brightness",
                "arguments": {"action": "down"}
            }
        if any(w in t for w in ["max brightness", "maximum brightness", "full brightness", "100% brightness"]):
            return {
                "intent": "action",
                "tool": "computer.brightness",
                "arguments": {"action": "max", "level": 100}
            }
        if any(w in t for w in ["dim brightness", "lowest brightness", "minimum brightness", "night brightness"]):
            return {
                "intent": "action",
                "tool": "computer.brightness",
                "arguments": {"action": "min", "level": 15}
            }
        if any(w in t for w in ["what is brightness", "check brightness", "screen brightness"]):
            return {
                "intent": "action",
                "tool": "computer.brightness",
                "arguments": {"action": "query"}
            }

        # 7. Hardware: Laptop Battery Diagnostics
        if any(w in t for w in ["laptop battery", "device battery", "battery status", "how much battery", "battery percentage", "check battery", "power status", "battery"]) and "phone" not in t and "mobile" not in t:
            return {
                "intent": "action",
                "tool": "computer.battery",
                "arguments": {}
            }

        # 8. Media Playback Controls (Pause, Resume, Next, Previous, Stop)
        if t in ["pause", "pause music", "pause video", "stop music", "pause media"]:
            return {
                "intent": "action",
                "tool": "computer.media_control",
                "arguments": {"action": "pause"}
            }
        if t in ["resume", "resume music", "play music", "unpause", "resume media"] and "youtube" not in t and "on " not in t:
            return {
                "intent": "action",
                "tool": "computer.media_control",
                "arguments": {"action": "play"}
            }
        if any(t == w or t.startswith(w) for w in ["next track", "next song", "skip song", "skip track", "next audio"]):
            return {
                "intent": "action",
                "tool": "computer.media_control",
                "arguments": {"action": "next"}
            }
        if any(t == w or t.startswith(w) for w in ["previous track", "previous song", "prev song", "last song", "back song"]):
            return {
                "intent": "action",
                "tool": "computer.media_control",
                "arguments": {"action": "previous"}
            }

        # 9. Desktop Window Controls (Minimize, Restore, Switch)
        if any(w in t for w in ["minimize all", "minimize all windows", "minimize windows", "show desktop", "minimize everything", "hide all windows", "minimize window", "minimize"]):
            return {
                "intent": "action",
                "tool": "computer.window_control",
                "arguments": {"action": "minimize_all"}
            }
        if any(w in t for w in ["restore windows", "unminimize windows", "show windows"]):
            return {
                "intent": "action",
                "tool": "computer.window_control",
                "arguments": {"action": "restore"}
            }
        if any(w in t for w in ["switch window", "alt tab", "next window"]):
            return {
                "intent": "action",
                "tool": "computer.window_control",
                "arguments": {"action": "switch"}
            }

        # 10. Hardware & Session Power (Lock, Sleep, Restart, Shutdown)
        if any(w in t for w in ["lock computer", "lock screen", "lock pc", "lock laptop", "lock workstation"]):
            return {
                "intent": "action",
                "tool": "computer.power",
                "arguments": {"action": "lock"}
            }
        if any(w in t for w in ["sleep mode", "sleep computer", "put laptop to sleep", "sleep pc", "sleep laptop", "sleep"]):
            return {
                "intent": "action",
                "tool": "computer.power",
                "arguments": {"action": "sleep"}
            }
        if any(w in t for w in ["restart computer", "restart laptop", "reboot pc"]):
            return {
                "intent": "action",
                "tool": "computer.power",
                "arguments": {"action": "restart"}
            }
        if any(w in t for w in ["shutdown computer", "turn off computer", "shutdown laptop", "power off pc"]):
            return {
                "intent": "action",
                "tool": "computer.power",
                "arguments": {"action": "shutdown"}
            }

        # 11. Screenshot Capture
        if any(w in t for w in ["screenshot", "take screenshot", "take a screenshot", "capture screen", "screen capture"]):
            return {
                "intent": "action",
                "tool": "computer.screenshot",
                "arguments": {}
            }

        # 12. System Diagnostics & Time
        if any(w in t for w in ["system status", "diagnostics", "system diagnostics", "laptop status", "cpu usage", "ram usage", "memory status", "what time", "what's the time", "what is the time", "current time", "what date", "today's date"]):
            return {
                "intent": "action",
                "tool": "computer.system_status",
                "arguments": {}
            }

        # 5. Specialized Cognitive Domains
        if any(kw in t for kw in ["study", "doubt", "explain", "physics", "chemistry", "biology", "calculus", "photosynthesis", "newton"]):
            return {
                "intent": "study",
                "tool": "study.solve",
                "arguments": {"question": raw_input}
            }

        if any(kw in t for kw in ["current situation", "present situation", "current affairs", "latest news", "who won", "election"]):
            return {
                "intent": "current_affairs",
                "tool": "current_affairs.brief",
                "arguments": {"query": raw_input}
            }

        if any(kw in t for kw in ["ai video", "runway", "sora", "kling", "luma", "video prompt"]):
            return {
                "intent": "ai_video",
                "tool": "ai_video.generate_prompt",
                "arguments": {"style_or_concept": raw_input}
            }

        if "antigravity" in t or "subagent" in t:
            return {
                "intent": "web_dev_antigravity",
                "tool": "antigravity.consult",
                "arguments": {"query": raw_input}
            }

        # 6. Phone & Mobile Agent Commands
        if t.startswith("call ") or t.startswith("dial ") or "phone call to " in t or "make a call to " in t:
            contact = t.replace("phone call to ", "").replace("make a call to ", "").replace("call ", "").replace("dial ", "").strip()
            return {
                "intent": "phone",
                "tool": "phone.call_contact",
                "arguments": {"contact": contact or "Unknown"}
            }

        if any(t.startswith(prefix) for prefix in ["send sms to ", "send message to ", "text ", "sms "]):
            cleaned = t
            for p in ["send sms to ", "send message to ", "text ", "sms "]:
                if cleaned.startswith(p):
                    cleaned = cleaned[len(p):].strip()
                    break
            parts = cleaned.split(" ", 1)
            contact = parts[0] if parts else "Contact"
            msg = parts[1] if len(parts) > 1 else "Hello from JARVIS"
            return {
                "intent": "phone",
                "tool": "phone.send_sms",
                "arguments": {"contact": contact, "message": msg}
            }

        if any(w in t for w in ["phone status", "mobile status", "phone battery", "battery of phone", "smartphone status"]):
            return {
                "intent": "phone",
                "tool": "phone.get_status",
                "arguments": {}
            }

        # 7. Math & Calculation
        if any(t.startswith(p) for p in ["calculate ", "solve "]) or (t.startswith("what is ") and any(op in t for op in ["+", "-", "*", "/", "%", "^", "times", "divided by"])):
            expr = t.replace("calculate ", "").replace("solve ", "").replace("what is ", "").strip()
            return {
                "intent": "calculator",
                "tool": "cognitive.calculate",
                "arguments": {"expression": expr}
            }

        # 8. Memory Management
        if t.startswith("remember that ") or t.startswith("remember "):
            fact = t.replace("remember that ", "").replace("remember ", "").strip()
            return {
                "intent": "memory",
                "tool": "cognitive.memory",
                "arguments": {"action": "save", "content": fact}
            }
        if any(t.startswith(p) for p in ["what do you remember about", "do you remember", "recall "]):
            query = t.replace("what do you remember about", "").replace("do you remember", "").replace("recall ", "").strip()
            return {
                "intent": "memory",
                "tool": "cognitive.memory",
                "arguments": {"action": "search", "content": query}
            }

        # 9. Default cognitive reasoning fallback (Chat / Knowledge / RAG)
        return {
            "intent": "chat",
            "tool": "cognitive.chat",
            "arguments": {"query": raw_input}
        }

orchestrator = UniversalOrchestrator()
