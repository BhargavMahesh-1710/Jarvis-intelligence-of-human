import os
import sys
import json
import time
import queue
import re
import urllib.request
import subprocess
from pathlib import Path

# Add project root and backend to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import sounddevice as sd
import vosk

from config import HOST, PORT, USER_NAME, PROJECT_ROOT
from core.agent import jarvis_agent, should_open_interface
from services.tts_service import speak_async, clean_text_for_speech

# Audio Configuration
SAMPLE_RATE = 16000
audio_queue = queue.Queue()

# State
is_speaking = False
last_command_time = 0
last_command_text = ""

WAKE_PATTERNS = [
    r"^(?:hey|hi|hello|ok|okay)?\s*jarvis\b",
    r"\bjarvis\b"
]

def is_server_running() -> bool:
    """Checks if JARVIS FastAPI backend is active on port 8000."""
    try:
        req = urllib.request.Request(f"http://{HOST}:{PORT}/health")
        with urllib.request.urlopen(req, timeout=1.5) as res:
            return res.status == 200
    except Exception:
        return False

def ensure_server_running():
    """Starts the FastAPI server in background if not already running."""
    if not is_server_running():
        print(f"[DAEMON] Starting JARVIS backend on http://{HOST}:{PORT}...")
        main_py = BACKEND_DIR / "main.py"
        if sys.platform == "win32":
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f'python "{str(main_py)}"'],
                cwd=str(PROJECT_ROOT)
            )
        else:
            subprocess.Popen([sys.executable, str(main_py)], cwd=str(PROJECT_ROOT))
        
        # Wait up to 6 seconds for server to come online
        for _ in range(12):
            time.sleep(0.5)
            if is_server_running():
                print("[DAEMON] Backend server is online.")
                break

def audio_callback(indata, frames, time_info, status):
    """Callback for sounddevice input stream."""
    if status:
        pass
    audio_queue.put(bytes(indata))

def extract_command_from_utterance(text: str) -> str:
    """
    Checks if utterance contains a wake phrase (e.g. 'hello jarvis', 'jarvis').
    Returns the stripped command, or None if no wake word was found.
    If the utterance was JUST 'hello jarvis', returns empty string '' to signal greeting.
    """
    t = text.lower().strip()
    
    # Check for leading greeting / wake words
    m = re.search(r"^(?:hey|hi|hello|ok|okay)?\s*jarvis[,\s:]*(.*)$", t)
    if m:
        return m.group(1).strip()
    
    # Check if 'jarvis' appears anywhere as an invocation
    m_any = re.search(r"\bjarvis\s+(.*)$", t)
    if m_any:
        return m_any.group(1).strip()
        
    return None

def handle_recognized_text(raw_text: str):
    """Processes a recognized speech string from the microphone."""
    global is_speaking, last_command_time, last_command_text
    
    if is_speaking:
        # Ignore audio while JARVIS is speaking to avoid feedback loops
        return

    text = raw_text.strip()
    if not text:
        return

    command = extract_command_from_utterance(text)
    if command is None:
        # No wake word present; ignore background conversation
        return

    now = time.time()
    # Debounce repeated triggers
    if command == last_command_text and (now - last_command_time) < 3.0:
        return

    last_command_time = now
    last_command_text = command

    print(f"\n[JARVIS DAEMON] Wake word detected! Raw: '{text}' -> Command: '{command}'")

    if not command:
        # User simply said "hello jarvis" or "jarvis"
        greeting = f"Online and listening, {USER_NAME}. What can I do for you?"
        print(f"[JARVIS DAEMON] Response: {greeting}")
        is_speaking = True
        t = speak_async(greeting)
        if t:
            t.join()
        is_speaking = False
        return

    # Process command through central JARVIS Agent
    try:
        res = jarvis_agent.process_request(command)
        must_open_ui = should_open_interface(res)
        reply = res.get("reply", f"Done, {USER_NAME}.")
        
        print(f"[JARVIS DAEMON] Result intent: {res.get('intent')} | Should open UI: {must_open_ui}")
        print(f"[JARVIS DAEMON] Reply: {reply}")

        # Headless vs Compulsory Interface Execution
        if must_open_ui:
            announcement = f"Opening JARVIS interface now, {USER_NAME}."
            is_speaking = True
            t = speak_async(announcement)
            
            # Open browser interface
            ui_url = f"http://{HOST}:{PORT}"
            try:
                import webbrowser
                webbrowser.open(ui_url)
            except Exception as e:
                print(f"[DAEMON] Failed to open browser: {e}")
                
            if t:
                t.join()
            is_speaking = False
        else:
            # HEADLESS: Speak reply out loud, UI stays completely closed
            is_speaking = True
            clean_reply = clean_text_for_speech(reply)
            t = speak_async(clean_reply)
            if t:
                t.join()
            is_speaking = False

    except Exception as e:
        err_msg = f"Sorry {USER_NAME}, I encountered an error: {str(e)}"
        print(f"[JARVIS DAEMON ERROR] {err_msg}")
        is_speaking = True
        t = speak_async(err_msg)
        if t:
            t.join()
        is_speaking = False

def run_daemon():
    """Main loop for the background voice listener daemon."""
    print("=" * 65)
    print(f"  [MAHI JARVIS] SYSTEM-WIDE BACKGROUND VOICE DAEMON ACTIVE")
    print(f"  Wake Words: 'Jarvis ...', 'Hello Jarvis ...', 'Hey Jarvis ...'")
    print(f"  Mode: Intelligent Headless Execution (Compulsory UI on Demand)")
    print("=" * 65)

    # Ensure backend server is running for memory & tool logging
    ensure_server_running()

    # Load Vosk Model
    print("[DAEMON] Initializing local offline speech recognition engine...")
    try:
        model = vosk.Model(lang="en-us")
        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        rec.SetWords(True)
    except Exception as e:
        print(f"[DAEMON FATAL] Failed to load Vosk model: {e}")
        return

    # Announce readiness
    ready_speech = f"JARVIS background service active, {USER_NAME}. Ready for your commands."
    speak_async(ready_speech)

    print("[DAEMON] Listening continuously to microphone in background...")
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype='int16',
                           channels=1, callback=audio_callback):
        while True:
            try:
                data = audio_queue.get()
                if rec.AcceptWaveform(data):
                    res_json = json.loads(rec.Result())
                    text = res_json.get("text", "")
                    if text:
                        handle_recognized_text(text)
                else:
                    # Partial speech
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    if partial and any(w in partial for w in ["jarvis", "jarvi"]):
                        # Quick early log for feedback
                        pass
            except KeyboardInterrupt:
                print("\n[DAEMON] Stopping voice listener...")
                break
            except Exception as e:
                print(f"[DAEMON LOOP ERROR] {e}")
                time.sleep(0.1)

if __name__ == "__main__":
    run_daemon()
