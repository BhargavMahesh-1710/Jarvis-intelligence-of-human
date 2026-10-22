import re
import json
import time
import requests
from typing import Dict, Any, List, Optional

from config import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    DEFAULT_MODEL,
    ASSISTANT_NAME,
    USER_NAME,
    REQUIRE_CONFIRMATION_FOR_ACTIONS,
    HOST,
    PORT
)
from core.memory import memory_store
from core.rag import rag_pipeline
from core.safety import safety_manager, PendingAction
from tools.calculator import calculate, calculator_tool
from tools.web_search import web_search, web_search_tool
from tools.files import files_tool, read_file, write_file, delete_file, list_files
from tools.browser import browser_tool
from tools.device_control import (
    open_app,
    close_app,
    open_url_or_site,
    play_on_youtube,
    take_screenshot,
    control_volume,
    control_brightness,
    get_battery_status,
    control_media,
    control_windows,
    control_power,
    lock_screen,
    get_system_status,
    find_and_open_laptop_file,
    list_laptop_folder,
    APP_REGISTRY
)
from core.intelligence import (
    classify_specialized_domain,
    handle_aux_screen_command,
    handle_study_doubt,
    handle_current_affairs,
    handle_web_dev_antigravity,
    handle_ai_video_creation
)
from services.ai_service import (
    ai_service,
    NOT_CONFIGURED_MESSAGE,
    OFFLINE_FALLBACK_MESSAGE
)

def open_jarvis_interface_tool() -> Dict[str, Any]:
    url = f"http://{HOST}:{PORT}"
    try:
        from tools.device_control import get_web_context
        if not get_web_context():
            import webbrowser
            webbrowser.open(url)
    except Exception:
        pass
    return {
        "success": True,
        "action": "open_interface",
        "action_type": "open_ui",
        "target": "JARVIS Interface",
        "url": url,
        "open_url": url,
        "message": f"Opening JARVIS Holographic Interface now, Mahi."
    }

def should_open_interface(result: Dict[str, Any]) -> bool:
    """
    Determines whether a command requires opening the JARVIS browser UI or should remain headless:
    - Compulsory (True):
      * Explicit request to open interface/dashboard/HUD/screen/JARVIS
      * Consequential action requiring user authorization (Protocol Alpha)
      * Explicit action_type == 'open_ui'
    - Headless (False):
      * Opening apps (Chrome, Notepad, Camera, etc.)
      * Opening files & folders (Documents, Downloads, Desktop, images, etc.)
      * Media playback (YouTube, songs, etc.)
      * Math & calculations
      * Question answering, system facts, and general chat
    """
    if not result:
        return False
    if result.get("pending_action"):
        return True
    if result.get("action_type") == "open_ui":
        return True
    if "open_jarvis_interface" in (result.get("tools_used") or []):
        return True
    return False

# Tool Registry Pattern from Blueprint
TOOLS = {
    "calculator": calculator_tool,
    "web_search": web_search_tool,
    "retrieve_memory": lambda query: "\n".join([f"- {m['fact']}" for m in memory_store.search_memory(query)]),
    "files": files_tool,
    "browser": browser_tool,
    "device_open_app": lambda app: open_app(app),
    "device_close_app": lambda app: close_app(app),
    "device_open_site": lambda site: open_url_or_site(site),
    "device_play_youtube": lambda query: play_on_youtube(query),
    "device_screenshot": lambda: take_screenshot(),
    "device_volume": lambda action="up", level=None: control_volume(action, level),
    "device_brightness": lambda action="up", level=None: control_brightness(action, level),
    "device_battery": lambda: get_battery_status(),
    "device_media": lambda action="play_pause": control_media(action),
    "device_windows": lambda action="minimize_all": control_windows(action),
    "device_power": lambda action="lock": control_power(action),
    "device_lock": lambda: lock_screen(),
    "device_system_status": lambda: get_system_status(),
    "device_find_and_open_file": lambda filename, preferred_folder="": find_and_open_laptop_file(filename, preferred_folder),
    "device_list_folder": lambda folder: list_laptop_folder(folder),
    "open_jarvis_interface": lambda: open_jarvis_interface_tool(),
    "aux_screen_display": lambda text: handle_aux_screen_command(text)
}

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Executes a registered tool with specified arguments."""
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    func = TOOLS[name]
    return func(**arguments)

def normalize_command(text: str) -> str:
    """
    Normalizes spoken / typed natural language commands:
    - Strips bot greetings / names ('jarvis', 'hey jarvis', 'assistant')
    - Strips polite / modal prefixes ('can you please', 'please', 'could you', 'i want you to', etc.)
    - Replaces elongated words ('opennn' -> 'open')
    - Maps gerunds / continuous verb forms to imperative ('opening' -> 'open', 'searching' -> 'search', etc.)
    """
    if not text:
        return ""
    t = text.lower().strip(" \t\r\n.,;:!?'\"`")

    # 1. Phonetic / spelling elongations & common contractions
    t = re.sub(r"\bopenn+\b", "open", t)
    t = re.sub(r"\blaunchh+\b", "launch", t)
    t = re.sub(r"\bple+a+se+\b", "please", t)
    t = re.sub(r"\byou\s+tube\b", "youtube", t)

    # 2. Leading conversational / bot greeting phrases
    t = re.sub(r"^(?:hey|hi|hello|ok|okay)?\s*(?:jarvis|assistant|computer)[,\s:]*", "", t).strip()

    # 3. Leading polite / modal verb requests
    t = re.sub(r"^(?:can\s+you\s+please|could\s+you\s+please|would\s+you\s+please|can\s+you|could\s+you|would\s+you|will\s+you|please|i\s+want\s+you\s+to|i\s+want\s+to|help\s+me\s+to|help\s+me)\s+", "", t).strip()
    t = re.sub(r"^please\s+", "", t).strip()

    # 4. Map gerund / continuous verb forms (-ing) to imperative
    verb_mappings = [
        (r"\bopening\b", "open"),
        (r"\bsearching\b", "search"),
        (r"\blaunching\b", "launch"),
        (r"\bstarting\b", "start"),
        (r"\brunning\b", "run"),
        (r"\bplaying\b", "play"),
        (r"\blistening\b", "listen"),
        (r"\bwatching\b", "watch"),
        (r"\bclosing\b", "close"),
        (r"\bkilling\b", "kill"),
        (r"\bexiting\b", "exit"),
        (r"\bterminating\b", "terminate"),
        (r"\btaking\b", "take"),
        (r"\bgoing\s+to\b", "go to"),
    ]
    for pattern, replacement in verb_mappings:
        t = re.sub(pattern, replacement, t)

    return t.strip(" \t\r\n.,;:!?'\"`")

class JarvisAgent:
    def __init__(self):
        self.assistant_name = ASSISTANT_NAME
        self.user_name = USER_NAME

    def call_gemini(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        """Calls Google Gemini API using REST endpoint."""
        if not GEMINI_API_KEY:
            return None
        
        model = "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        contents = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Directive: {system_instruction}\n\nUser Request: {prompt}"}]
            })
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

        try:
            resp = requests.post(url, headers=headers, json={"contents": contents}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            print(f"Gemini API error: {resp.status_code} {resp.text}")
            return None
        except Exception as e:
            print(f"Gemini API request failed: {e}")
            return None

    def call_openai(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        """Calls OpenAI service using official SDK via ai_service."""
        if not ai_service.is_configured():
            return None
        return ai_service.ask_ai(prompt, context=system_instruction)

    def call_llm(self, prompt: str, system_instruction: Optional[str] = None, context: Optional[str] = None, is_current: bool = False) -> str:
        """Invokes active LLM provider (OpenAI ai_service / Gemini) or falls back to local intelligent synthesis."""
        if ai_service.is_configured():
            return ai_service.ask_ai(prompt, context=context or system_instruction, is_current=is_current)

        if GEMINI_API_KEY:
            res = self.call_gemini(prompt, system_instruction)
            if res:
                return res

        return self._local_synthesize(prompt, system_instruction)

    def _local_synthesize(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Smart offline synthesis engine when no external API key is active."""
        p_lower = prompt.lower().strip()
        
        # Greetings
        if any(w in p_lower for w in ["hello", "hi jarvis", "hey jarvis", "good morning", "good evening"]):
            return f"Greetings, {self.user_name}. Neural core online and ready. All computer control protocols active."

        # Identity questions
        if "who are you" in p_lower or "what is your name" in p_lower:
            return f"I am {self.assistant_name}, your personal AI assistant. I have full computer and device control capabilities, long-term memory, voice recognition, and real-time reasoning."

        # Status check
        if "system status" in p_lower or "diagnostic" in p_lower or "diagnostics" in p_lower:
            mem_count = len(memory_store.load_memory())
            doc_count = len(rag_pipeline.load_documents())
            now = time.strftime("%I:%M %p, %B %d, %Y")
        # Specialized domain checks
        spec = classify_specialized_domain(prompt)
        if spec == "ai_video":
            return handle_ai_video_creation(prompt, self.user_name)["reply"]
        elif spec == "web_dev_antigravity":
            return handle_web_dev_antigravity(prompt, self.user_name)["reply"]
        elif spec == "current_affairs":
            return handle_current_affairs(prompt, self.user_name)["reply"]
        elif spec == "study":
            return handle_study_doubt(prompt, self.user_name)["reply"]
        elif spec == "aux_screen":
            return handle_aux_screen_command(prompt)["reply"]

        # Search-augmented general synthesis
        search_res = web_search(prompt, max_results=3)
        if search_res and not search_res[0]["snippet"].startswith("Web results unavailable"):
            items = "\n".join([f"- **{r['title']}**: {r['snippet']}" for r in search_res])
            return f"Based on live satellite intelligence records regarding '{prompt}':\n\n{items}"

        return f"Understood, {self.user_name}. Neural core processed: '{prompt}'."

    def classify_intent(self, text: str) -> str:
        """
        Classifies user request into one of the blueprint intents:
        'aux_screen', 'ai_video', 'web_dev_antigravity', 'current_affairs', 'study',
        'action' (device/file control), 'calculator', 'search', 'memory', 'document', 'chat'
        """
        t = normalize_command(text)

        # 0. Specialized High-Priority Domain Classification
        spec_domain = classify_specialized_domain(text)
        if spec_domain == "aux_screen":
            return "aux_screen"
        if spec_domain in ["ai_video", "web_dev_antigravity", "current_affairs"]:
            return spec_domain

        # YouTube and Music Actions
        if "youtube" in t or (("play" in t or "listen" in t) and ("song" in t or "music" in t or "video" in t or "track" in t)):
            return "action"

        # Direct Device & OS Control Commands
        device_verbs = [
            "open ", "launch ", "start ", "run ", "close ", "kill ", "exit ",
            "play ", "watch ", "go to ", "screenshot", "take screenshot", "mute", "unmute",
            "volume up", "volume down", "lock screen", "lock computer",
            "what time", "what's the time", "what is the time", "current time", "what date", "today's date", "time now",
            "delete file", "remove file", "create file", "write file", "save file",
            "list ", "show files", "find file", "open file"
        ]
        if any(t.startswith(verb) or f" {verb}" in f" {t}" for verb in device_verbs):
            return "action"
        if re.search(r"\b(?:list|show|view)\s+(?:the\s+)?(?:files\s+in\s+|all\s+files\s+in\s+)?(documents|downloads|desktop|pictures|videos|music|workspace)", t):
            return "action"
        if re.search(r"\b(?:open|find)\s+(?:the\s+)?(?:file|document)\b", t):
            return "action"

        # Check if t is directly an application, folder, or hardware feature (e.g. "document", "chrome", "camera", "notepad")
        known_direct_targets = list(APP_REGISTRY.keys()) + [
            "chrome", "google chrome", "notepad", "calculator", "calc", "camera", "paint",
            "vscode", "terminal", "cmd", "settings", "documents", "downloads", "desktop",
            "document", "doc", "docs", "download", "picture", "pictures", "photo", "photos",
            "video", "videos", "music", "interface", "dashboard", "hud"
        ]
        if t in known_direct_targets or any(t.startswith(f"{app} ") for app in known_direct_targets):
            return "action"

        # Check for web site opening / searching (e.g. "naruto on animerulz", "one piece on crunchyroll", "google python")
        anime_sites = "animerulz|anime|crunchyroll|hianime|aniwatch|zoro|9anime|aniwave|gogoanime|anitaku|animepahe|kickassanime|kaas|animesuge|animeflv|myanimelist|mal|anilist|bilibili|hidive"
        if re.search(rf"\b(?:in|on|at|from)\s+(?:{anime_sites}|chrome|youtube|google|amazon|flipkart|reddit|wikipedia|github|netflix|spotify)\b", t):
            return "action"
        if any(kw in t for kw in ["watch anime", "anime", "one piece", "naruto", "bleach", "demon slayer", "jujutsu kaisen", "solo leveling", "attack on titan", "dragon ball", "death note", "hunter x hunter", "chainsaw man"]):
            if any(t.startswith(verb) for verb in ["watch", "open", "play", "search", "stream"]):
                return "action"

        # Academic / Study Doubts
        if spec_domain == "study":
            return "study"

        # Math / Calculator
        if any(t.startswith(w) for w in ["calculate", "what is", "evaluate", "solve", "math"]):
            if any(sym in t for sym in ["+", "-", "*", "/", "^", "%", "sqrt", "times", "divided"]):
                return "calculator"
        if re.search(r"\d+\s*[\+\-\*\/x\^]\s*\d+", t):
            return "calculator"

        # Memory store or recall
        if any(kw in t for kw in ["remember that", "remember this", "don't forget that", "save to memory", "note that"]):
            return "memory"
        if any(kw in t for kw in ["what is my", "who am i", "what do you remember", "my favorite", "where do i live", "my preferences"]):
            return "memory"

        # Document / RAG search (prioritize local docs when matched)
        doc_keywords = [
            "in the manual", "in the document", "knowledge base", "project blueprint",
            "documentation", "according to the doc", "protocol", "protocols", "manual",
            "jarvis manual"
        ]
        if any(kw in t for kw in doc_keywords):
            return "document"

        # Check if local knowledge base has very relevant match (Local RAG priority)
        rag_matches = rag_pipeline.retrieve(text, top_k=1)
        if rag_matches and rag_matches[0].get("score", 0) > 0.4:
            return "document"

        # Web search & Current Information questions
        search_keywords = [
            "search web", "search for", "google", "look up online", "who won",
            "latest news", "latest", "today's", "today", "current", "recent", "now",
            "weather in", "weather", "current population", "prime minister",
            "who is the current", "what is the current", "news about", "score of"
        ]
        if any(kw in t for kw in search_keywords):
            return "search"

        return "chat"

    def plan_and_execute_task(self, request: str) -> Dict[str, Any]:
        """
        Intelligent Device & Task Controller (Algorithm C):
        Executes instructions given by the user on their device or system.
        """
        t = normalize_command(request)
        steps = []
        tools_used = []

        # 0. Open JARVIS Holographic Interface / Dashboard
        if re.search(r"\b(?:open|show|launch|start|display)\s+(?:the\s+)?(?:jarvis\s+)?(?:interface|dashboard|hud|screen|ui|gui)\b|\b(?:open|launch|show)\s+(?:my\s+)?jarvis\b", t):
            step = {
                "step": 1,
                "tool": "open_jarvis_interface",
                "args": {},
                "is_consequential": False,
                "description": "Open JARVIS Holographic Interface"
            }
            steps.append(step)

        # 1. YouTube Playback & Search (handles "open youtube and play telugu songs", "open the youtube", "play telugu songs on youtube", etc.)
        elif "youtube" in t or t.startswith("play ") or (("play " in t or "listen " in t) and ("song" in t or "music" in t or "video" in t or "track" in t)):
            query = ""
            if re.fullmatch(r"(?:open|launch|start|go\s+to)?\s*(?:the\s+)?youtube", t.strip()):
                query = ""
            else:
                m1 = re.search(r"(?:open|launch|start)?\s*(?:the\s+)?youtube\s*(?:and\s+|to\s+)?(?:play|search|find|listen to)?\s*(?:for\s+)?(.*)", t)
                if m1 and m1.group(1).strip():
                    query = m1.group(1).strip()
                else:
                    m2 = re.search(r"(?:play|search|find|listen to)\s+(?:for\s+)?(.*?)(?:\s+(?:on|in|at|from)\s+youtube|$)", t)
                    if m2 and m2.group(1).strip():
                        query = m2.group(1).strip()
                    elif t.startswith("play "):
                        query = re.sub(r"^play\s+", "", t).strip()

            # Clean query prefixes & suffixes
            for p in ["and play a", "and play an", "and play the", "and play", "to play a", "to play", "play a", "play an", "play the", "play", "search for", "search", "and search", "watch"]:
                if query.lower().startswith(p):
                    query = query[len(p):].strip()
            for s in ["on youtube", "in youtube", "at youtube"]:
                if query.lower().endswith(s):
                    query = query[:-len(s)].strip()
            query = re.sub(r"^(?:a|an|the)\s+", "", query, flags=re.IGNORECASE).strip(" '\":")

            step = {
                "step": 1,
                "tool": "device_play_youtube",
                "args": {"query": query},
                "is_consequential": False,
                "description": f"Play '{query}' on YouTube" if query else "Open YouTube"
            }
            steps.append(step)

        # 2. Folder Listing (e.g. "list documents", "show files in downloads", "list files in desktop")
        elif re.search(r"\b(?:list|show|view)\s+(?:the\s+)?(?:files\s+in\s+|all\s+files\s+in\s+)?(documents|downloads|desktop|pictures|videos|music|workspace)(?:\s+files|\s+folder|\s+directory)?\b", t) and not any(w in t for w in ["open", "play", "run", "watch"]):
            m_folder = re.search(r"\b(?:list|show|view)\s+(?:the\s+)?(?:files\s+in\s+|all\s+files\s+in\s+)?(documents|downloads|desktop|pictures|videos|music|workspace)", t)
            target_fld = m_folder.group(1).strip() if m_folder else "documents"
            step = {
                "step": 1,
                "tool": "device_list_folder",
                "args": {"folder": target_fld},
                "is_consequential": False,
                "description": f"List files in laptop folder '{target_fld}'"
            }
            steps.append(step)

        # 3. Location-specified File or Folder Opening (e.g. "open jarvi interface jpj in desktop", "open resume in documents", "open setup in downloads")
        m_loc_file = re.search(r"\b(?:open|launch|find|view)\s+(?:the\s+)?(?:file\s+|document\s+|image\s+|pic\s+|photo\s+)?(.+?)\s+(?:in|on|from|at)\s+(?:the\s+)?(?:my\s+)?(desktop|documents|downloads|pictures|videos|music|workspace)\b", t, re.IGNORECASE)
        if m_loc_file and not any(w in t for w in ["youtube", "crunchyroll", "animerulz"]):
            raw_fn = m_loc_file.group(1).strip()
            loc_fld = m_loc_file.group(2).strip().lower()
            if raw_fn and raw_fn not in ["the", "my", "folder", "directory"]:
                step = {
                    "step": 1,
                    "tool": "device_find_and_open_file",
                    "args": {"filename": raw_fn, "preferred_folder": loc_fld},
                    "is_consequential": False,
                    "description": f"Find and open '{raw_fn}' in {loc_fld} on your laptop"
                }
                steps.append(step)

        # 4. Direct Laptop File Opening by Extension or Keyword (e.g. "open file notes.txt", "open report.pdf", "open jarvi interface.jpeg")
        if not steps and (re.search(r"\b(?:open|launch|find|view)\s+(?:the\s+)?(?:file\s+|document\s+|image\s+|pic\s+|photo\s+)?([a-zA-Z0-9_\-\s]+\.(?:pdf|txt|docx?|xlsx?|pptx?|csv|json|py|html|png|jpg|jpeg|jpj|mp4|mp3|zip))\b", request, re.IGNORECASE) or re.search(r"\bopen\s+file\s+([a-zA-Z0-9_\-\.\s]+)", request, re.IGNORECASE)):
            m_f = re.search(r"\b(?:open|launch|find|view)\s+(?:the\s+)?(?:file\s+|document\s+|image\s+|pic\s+|photo\s+)?([a-zA-Z0-9_\-\s]+\.(?:pdf|txt|docx?|xlsx?|pptx?|csv|json|py|html|png|jpg|jpeg|jpj|mp4|mp3|zip))\b", request, re.IGNORECASE)
            if not m_f:
                m_f = re.search(r"\bopen\s+file\s+([a-zA-Z0-9_\-\.\s]+)", request, re.IGNORECASE)
            filename = m_f.group(1).strip()
            step = {
                "step": 1,
                "tool": "device_find_and_open_file",
                "args": {"filename": filename},
                "is_consequential": False,
                "description": f"Find and open file '{filename}' on your laptop"
            }
            steps.append(step)

        # 5. Launching Desktop Applications, Laptop Folders, Hardware Features, or Websites
        if not steps:
            # Known desktop applications, system folders, and laptop hardware features
            desktop_apps = list(APP_REGISTRY.keys()) + [
                "chrome", "google chrome", "notepad", "calculator", "calc", "edge",
                "microsoft edge", "firefox", "explorer", "files", "file explorer",
                "cmd", "command prompt", "terminal", "powershell", "code", "vscode",
                "vs code", "spotify", "paint", "mspaint", "task manager", "settings",
                "word", "excel", "vlc", "documents", "downloads", "desktop", "pictures",
                "videos", "music", "camera", "wifi", "bluetooth", "battery",
                "control panel", "device manager", "snipping tool",
                "document", "my document", "docs", "doc", "my docs", "my doc",
                "download", "my download", "picture", "photo", "photos", "video"
            ]

            target = re.sub(r"^(?:open|launch|start|run|search|watch|play|stream|go\s+to)\s+(?:the\s+)?", "", t).strip()
            is_explicit_browser = bool(re.search(r"\b(?:in|on)\s+(?:chrome|google\s+chrome|browser|web\s+browser)\b", target))
            clean_target = re.sub(r"\b(?:in|on)\s+(?:chrome|google\s+chrome|browser|web\s+browser)\b", "", target).strip()
            clean_target = re.sub(r"\s+(?:folder|directory|app|application)$", "", clean_target).strip()
            if clean_target.startswith("my "):
                alt = clean_target[3:].strip()
                if alt in desktop_apps:
                    clean_target = alt

            has_verb = any(t.startswith(verb) for verb in ["open ", "launch ", "start ", "run ", "search ", "watch ", "play ", "stream ", "go to "])
            has_web_domain = bool(re.search(r"\b(?:in|on|at|from)\s+(?:animerulz|anime|crunchyroll|hianime|aniwatch|zoro|9anime|aniwave|gogoanime|anitaku|animepahe|kickassanime|kaas|animesuge|animeflv|myanimelist|mal|anilist|bilibili|hidive|chrome|google\s+chrome|browser|amazon|flipkart|reddit|wikipedia|github|netflix|spotify)\b", t))
            is_direct_app = (clean_target in desktop_apps or t in desktop_apps or clean_target.endswith(".exe"))

            if has_verb or is_direct_app or has_web_domain:
                if not is_explicit_browser and (is_direct_app or clean_target in ["app"]):
                    app_name = "chrome" if clean_target in ["browser", "web browser"] else (clean_target or t)
                    step = {
                        "step": 1,
                        "tool": "device_open_app",
                        "args": {"app": app_name},
                        "is_consequential": False,
                        "description": f"Open '{app_name}' on your laptop"
                    }
                    steps.append(step)
                elif has_verb or has_web_domain:
                    # All other targets are web, online platform, or browser search actions
                    step = {
                        "step": 1,
                        "tool": "device_open_site",
                        "args": {"site": target},
                        "is_consequential": False,
                        "description": f"Open '{target}' in Chrome"
                    }
                    steps.append(step)


        # 3. Close Applications (e.g. "close chrome", "exit notepad", "kill spotify")
        if not steps and any(t.startswith(verb) for verb in ["close ", "exit ", "kill ", "terminate "]):
            target = re.sub(r"^(?:close|exit|kill|terminate)\s+(?:the\s+)?", "", t).strip()
            step = {
                "step": 1,
                "tool": "device_close_app",
                "args": {"app": target},
                "is_consequential": False,
                "description": f"Close application '{target}'"
            }
            steps.append(step)

        # 4. Take Screenshot
        if not steps and "screenshot" in t:
            step = {
                "step": 1,
                "tool": "device_screenshot",
                "args": {},
                "is_consequential": False,
                "description": "Capture screen snapshot"
            }
            steps.append(step)

        # 5. Volume Controls (mute, unmute, volume up, volume down)
        if not steps and any(w in t for w in ["mute", "unmute", "volume"]):
            act = "mute" if "mute" in t else ("up" if "up" in t or "increase" in t else "down")
            step = {
                "step": 1,
                "tool": "device_volume",
                "args": {"action": act},
                "is_consequential": False,
                "description": f"Adjust volume ({act})"
            }
            steps.append(step)

        # 6. Lock Screen
        if not steps and ("lock screen" in t or "lock computer" in t or "lock pc" in t):
            step = {
                "step": 1,
                "tool": "device_lock",
                "args": {},
                "is_consequential": False,
                "description": "Lock computer workstation"
            }
            steps.append(step)

        # 7. Time / Date / System Status
        if not steps and any(w in t for w in ["what time", "what's the time", "what is the time", "current time", "what date", "today's date", "time now"]):
            step = {
                "step": 1,
                "tool": "device_system_status",
                "args": {},
                "is_consequential": False,
                "description": "Query system clock and date"
            }
            steps.append(step)

        # 8. File Operations (write / create file)
        match_write = re.search(r"(?:create|write|save)\s+(?:a\s+)?file\s+(?:named\s+)?([A-Za-z0-9_\-\.]+)\s+(?:with\s+(?:the\s+)?(?:content|text|data)\s+)?['\"]?(.*?)['\"]?$", request, re.IGNORECASE)
        if match_write and ("create" in t or "write" in t or "save" in t):
            fname = match_write.group(1).strip()
            content = match_write.group(2).strip() or "Sample file generated by JARVIS."
            step = {
                "step": 1,
                "tool": "files",
                "args": {"action": "write", "filename": fname, "content": content},
                "is_consequential": False,  # Writing is safe in workspace
                "description": f"Write {len(content)} bytes to file '{fname}' in workspace"
            }
            steps.append(step)

        # 9. File Deletion (Consequential - requires confirmation)
        match_del = re.search(r"(?:delete|remove)\s+(?:the\s+)?file\s+([A-Za-z0-9_\-\.]+)", request, re.IGNORECASE)
        if match_del:
            fname = match_del.group(1).strip()
            step = {
                "step": 1,
                "tool": "files",
                "args": {"action": "delete", "filename": fname},
                "is_consequential": True,  # Destructive action
                "description": f"Permanently delete file '{fname}' from workspace"
            }
            steps.append(step)

        # Execute Plan Steps
        if not steps:
            # If frontier LLM is present, ask it to synthesize a response or plan
            llm_reply = self.call_llm(request)
            return {
                "reply": llm_reply,
                "plan": [],
                "tools_used": [],
                "pending_action": None
            }

        plan_summary = []
        execution_replies = []
        open_url = None
        action_type = None
        target = None
        folder_path = None
        folder_name = None
        files = None
        file_url = None
        is_image = None
        path = None
        embed_url = None
        video_id = None
        action = None

        for s in steps:
            plan_summary.append(f"{s['description']}")
            if s["is_consequential"]:
                # Pause and request user confirmation
                pending = safety_manager.create_pending_action(
                    tool_name=s["tool"],
                    arguments=s["args"],
                    description=s["description"]
                )
                return {
                    "reply": f"⚠️ Consequential action detected: {s['description']}. Awaiting your confirmation to execute.",
                    "plan": plan_summary,
                    "tools_used": [s["tool"]],
                    "pending_action": {
                        "action_id": pending.action_id,
                        "tool": pending.tool_name,
                        "description": pending.description
                    },
                    "open_url": None,
                    "action_type": None,
                    "target": None,
                    "folder_path": None,
                    "folder_name": None,
                    "files": None,
                    "file_url": None,
                    "is_image": None,
                    "path": None,
                    "embed_url": None,
                    "video_id": None,
                    "action": None
                }
            else:
                # Execute device action immediately
                res = execute_tool(s["tool"], s["args"])
                tools_used.append(s["tool"])
                if isinstance(res, dict):
                    if res.get("url"):
                        open_url = res["url"]
                    if res.get("action_type"):
                        action_type = res["action_type"]
                    if res.get("target"):
                        target = res["target"]
                    if res.get("folder_path"):
                        folder_path = res["folder_path"]
                    if res.get("folder_name"):
                        folder_name = res["folder_name"]
                    if res.get("files"):
                        files = res["files"]
                    if res.get("file_url"):
                        file_url = res["file_url"]
                    if res.get("is_image") is not None:
                        is_image = res["is_image"]
                    if res.get("path"):
                        path = res["path"]
                    if res.get("embed_url"):
                        embed_url = res["embed_url"]
                    if res.get("video_id"):
                        video_id = res["video_id"]
                    if res.get("action"):
                        action = res["action"]
                    msg = res.get("message", str(res))
                else:
                    msg = str(res)
                execution_replies.append(msg)
                safety_manager.log_event(s["tool"], s["args"], "completed", msg, is_consequential=False)

        reply_text = "\n".join(execution_replies) if execution_replies else f"Instruction completed, {self.user_name}."
        return {
            "reply": reply_text,
            "plan": plan_summary,
            "tools_used": tools_used,
            "pending_action": None,
            "open_url": open_url,
            "action_type": action_type,
            "target": target,
            "folder_path": folder_path,
            "folder_name": folder_name,
            "files": files,
            "file_url": file_url,
            "is_image": is_image,
            "path": path,
            "embed_url": embed_url,
            "video_id": video_id,
            "action": action
        }

    def process_request(self, user_message: str) -> Dict[str, Any]:
        """
        Central AI Pipeline:
        1. Fact extraction & long-term memory
        2. Intent routing & execution (Device Control / Math / Web / RAG / Chat)
        """
        # Step 1: Extract and store personal facts
        extracted_facts = memory_store.extract_facts(user_message)
        for fact in extracted_facts:
            memory_store.save_memory(fact)

        # Step 2: Classify Intent
        intent = self.classify_intent(user_message)
        tools_used = []
        pending_action = None
        plan = []
        open_url = None
        action_type = None
        target = None
        folder_path = None
        folder_name = None
        files = None
        file_url = None
        is_image = None
        path = None
        embed_url = None
        video_id = None
        action = None
        aux_display = None

        if intent == "aux_screen":
            res = handle_aux_screen_command(user_message)
            reply = res["reply"]
            aux_display = res.get("aux_display")
            tools_used.append("aux_screen_control")

        elif intent == "study":
            if ai_service.is_configured():
                ai_reply = ai_service.ask_ai(user_message)
                if ai_reply and ai_reply not in [NOT_CONFIGURED_MESSAGE, OFFLINE_FALLBACK_MESSAGE]:
                    reply = ai_reply
                    tools_used.append("study_solver")
                    tools_used.append("ai_service")
                else:
                    res = handle_study_doubt(user_message, self.user_name)
                    reply = res["reply"]
                    aux_display = res.get("aux_display")
                    tools_used.append("study_solver")
            else:
                res = handle_study_doubt(user_message, self.user_name)
                reply = res["reply"]
                aux_display = res.get("aux_display")
                tools_used.append("study_solver")

        elif intent == "current_affairs":
            res = handle_current_affairs(user_message, self.user_name)
            reply = res["reply"]
            aux_display = res.get("aux_display")
            tools_used.append("current_affairs_scanner")

        elif intent == "web_dev_antigravity":
            res = handle_web_dev_antigravity(user_message, self.user_name)
            reply = res["reply"]
            aux_display = res.get("aux_display")
            tools_used.append("antigravity_web_architect")

        elif intent == "ai_video":
            res = handle_ai_video_creation(user_message, self.user_name)
            reply = res["reply"]
            aux_display = res.get("aux_display")
            tools_used.append("generative_video_director")

        elif intent == "action":
            plan_res = self.plan_and_execute_task(user_message)
            reply = plan_res["reply"]
            plan = plan_res["plan"]
            tools_used = plan_res["tools_used"]
            pending_action = plan_res["pending_action"]
            open_url = plan_res.get("open_url")
            action_type = plan_res.get("action_type")
            target = plan_res.get("target")
            folder_path = plan_res.get("folder_path")
            folder_name = plan_res.get("folder_name")
            files = plan_res.get("files")
            file_url = plan_res.get("file_url")
            is_image = plan_res.get("is_image")
            path = plan_res.get("path")
            embed_url = plan_res.get("embed_url")
            video_id = plan_res.get("video_id")
            action = plan_res.get("action")

        elif intent == "calculator":
            calc_res = calculate(user_message)
            tools_used.append("calculator")
            safety_manager.log_event("calculator", {"expression": user_message}, "success", calc_res, False)
            if calc_res["success"]:
                reply = f"The result is: **{calc_res['result']}**"
            else:
                reply = f"I could not calculate that: {calc_res.get('error')}"

        elif intent == "search":
            search_data = web_search(user_message)
            tools_used.append("web_search")
            safety_manager.log_event("web_search", {"query": user_message}, "success", f"{len(search_data)} results", False)
            context = "\n".join([f"- **{r['title']}**: {r['snippet']} ({r['link']})" for r in search_data])
            tools_used.append("ai_service")
            reply = ai_service.ask_ai(user_message, context=context, is_current=True)

        elif intent == "memory":
            relevant = memory_store.search_memory(user_message)
            tools_used.append("retrieve_memory")
            if relevant:
                facts_str = "\n".join([f"• {r['fact']}" for r in relevant])
                reply = f"Based on my memory records:\n{facts_str}"
            elif extracted_facts:
                reply = f"Understood, {self.user_name}. I have committed that to memory: '{extracted_facts[0]}'."
            else:
                recent = memory_store.recent_memory(5)
                if recent:
                    facts_str = "\n".join([f"• {r['fact']}" for r in recent])
                    reply = f"I do not have a specific match for that, but here is what I currently recall:\n{facts_str}"
                else:
                    reply = "My memory banks are currently empty. You can tell me facts by saying 'Remember that...'."

        elif intent == "document":
            chunks = rag_pipeline.retrieve(user_message, top_k=3)
            tools_used.append("rag_retrieval")
            if chunks:
                sources = list(set([c["source"] for c in chunks]))
                if ai_service.is_configured():
                    prompt = rag_pipeline.build_prompt(user_message, chunks)
                    reply = ai_service.ask_ai(prompt, context=f"Sources: {', '.join(sources)}")
                    tools_used.append("ai_service")
                elif GEMINI_API_KEY:
                    prompt = rag_pipeline.build_prompt(user_message, chunks)
                    reply = self.call_gemini(prompt, "You are JARVIS. Answer the question using the provided context.")
                else:
                    best_chunk = chunks[0]["text"]
                    reply = f"According to knowledge file **{sources[0]}**:\n\n> {best_chunk}\n\n*(Sources cited: {', '.join(sources)})*"
            else:
                reply = "I checked the knowledge repository, but found no relevant documents matching your query. You can add documents to `backend/data/knowledge`."

        else: # "chat"
            mem = memory_store.search_memory(user_message, top_k=2)
            context = ""
            if mem:
                context = f"Relevant user memory: {'; '.join([m['fact'] for m in mem])}"
            
            p_lower = user_message.lower().strip()
            if not ai_service.is_configured() and any(w in p_lower for w in ["hello", "hi jarvis", "hey jarvis", "who are you", "system status", "diagnostic"]):
                reply = self._local_synthesize(user_message)
            else:
                tools_used.append("ai_service")
                reply = ai_service.ask_ai(user_message, context=context)

        return {
            "reply": reply,
            "intent": intent,
            "tools_used": tools_used,
            "plan": plan,
            "pending_action": pending_action,
            "open_url": open_url,
            "action_type": action_type,
            "target": target,
            "folder_path": folder_path,
            "folder_name": folder_name,
            "files": files,
            "file_url": file_url,
            "is_image": is_image,
            "path": path,
            "embed_url": embed_url,
            "video_id": video_id,
            "action": action,
            "aux_display": aux_display
        }

jarvis_agent = JarvisAgent()
