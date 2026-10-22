import sys
import subprocess
import threading
import re

def clean_text_for_speech(text: str) -> str:
    """Strips markdown formatting, URLs, code blocks, and emojis for natural speech."""
    if not text:
        return ""
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove URLs
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    # Remove markdown symbols (*, _, `, #, ~, >, •)
    cleaned = re.sub(r'[\*\_`#~>•]', '', cleaned)
    # Remove bullet list markers like "• " or "- "
    cleaned = re.sub(r'^\s*[\-\*]\s+', '', cleaned, flags=re.MULTILINE)
    # Remove multiple spaces/newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Remove quotes that might break PowerShell arguments
    cleaned = cleaned.replace('"', '').replace("'", "")
    return cleaned

def _speak_worker(clean_text: str):
    """Executes Windows native System.Speech synthesizer without blocking."""
    if not clean_text:
        return
    if sys.platform == "win32":
        try:
            # Use PowerShell System.Speech.Synthesis
            ps_command = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Rate = 1; "
                f"$s.Speak('{clean_text}')"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_command],
                capture_output=True,
                timeout=25
            )
        except Exception as e:
            print(f"[TTS Error] Speech synthesis failed: {e}")
    else:
        # Fallback for Linux/macOS
        try:
            subprocess.run(["espeak", clean_text], capture_output=True, timeout=15)
        except Exception:
            pass

def speak_async(text: str):
    """Asynchronously speaks text in a background daemon thread."""
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        return None
    thread = threading.Thread(target=_speak_worker, args=(cleaned,), daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    print("Testing TTS service...")
    t = speak_async("Hello Mahi, JARVIS voice synthesis is operational.")
    if t:
        t.join()
    print("TTS test completed.")
