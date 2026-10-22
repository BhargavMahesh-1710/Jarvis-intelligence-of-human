import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import MEMORY_FILE

class MemoryStore:
    def __init__(self, filepath: Path = MEMORY_FILE):
        self.filepath = Path(filepath)
        self._ensure_file()

    def _ensure_file(self):
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text("[]", encoding="utf-8")

    def load_memory(self) -> List[Dict[str, Any]]:
        """Loads all stored memories from the JSON store."""
        if not self.filepath.exists():
            return []
        try:
            content = self.filepath.read_text(encoding="utf-8")
            return json.loads(content) if content.strip() else []
        except Exception:
            return []

    def save_memory(self, item: Any) -> Dict[str, Any]:
        """Saves a memory item into persistent storage."""
        memory = self.load_memory()
        
        # Standardize entry format
        if isinstance(item, str):
            record = {
                "id": len(memory) + 1,
                "fact": item.strip(),
                "timestamp": time.time(),
                "source": "user_interaction"
            }
        elif isinstance(item, dict):
            record = item
            if "id" not in record:
                record["id"] = len(memory) + 1
            if "timestamp" not in record:
                record["timestamp"] = time.time()
        else:
            record = {
                "id": len(memory) + 1,
                "fact": str(item),
                "timestamp": time.time()
            }

        # Prevent exact duplicate facts
        for existing in memory:
            if existing.get("fact", "").lower() == record.get("fact", "").lower():
                return existing

        memory.append(record)
        self.filepath.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
        return record

    def recent_memory(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent memories up to the specified limit."""
        return self.load_memory()[-limit:]

    def search_memory(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memory items using keyword overlap and term scoring.
        """
        memories = self.load_memory()
        if not memories:
            return []

        query_tokens = set(re.findall(r"\w+", query.lower()))
        # Filter out common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "who", "where", "my", "your", "in", "on", "of", "to", "do", "you", "know"}
        meaningful_tokens = query_tokens - stop_words
        if not meaningful_tokens:
            meaningful_tokens = query_tokens

        scored = []
        for item in memories:
            fact_text = item.get("fact", "").lower()
            fact_tokens = set(re.findall(r"\w+", fact_text))
            
            # Intersection score
            common = meaningful_tokens.intersection(fact_tokens)
            if common:
                score = len(common) / max(len(meaningful_tokens), 1)
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def extract_facts(self, text: str) -> List[str]:
        """
        Extracts stable, useful personal facts or preferences from user statements.
        Examples:
        - "Remember that my favorite fruit is mango"
        - "My name is Mahi"
        - "I prefer dark mode"
        """
        facts = []
        patterns = [
            r"(?:please\s+)?remember\s+(?:that\s+)?(.+)",
            r"my\s+name\s+is\s+([A-Za-z0-9_\s]+)",
            r"i\s+prefer\s+([^\.]+)",
            r"my\s+favorite\s+([^\.]+)",
            r"i\s+like\s+([^\.]+)",
            r"i\s+am\s+a\s+([^\.]+)",
            r"i\s+live\s+in\s+([^\.]+)",
            r"i\s+work\s+as\s+([^\.]+)",
        ]
        
        for pat in patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                fact = m.group(1).strip()
                # Clean punctuation at end
                fact = re.sub(r"[.?!]+$", "", fact).strip()
                if fact and len(fact) > 2:
                    if "remember" in pat:
                        facts.append(fact)
                    elif "name is" in pat:
                        facts.append(f"User's name is {fact.title()}")
                    elif "prefer" in pat:
                        facts.append(f"User prefers {fact}")
                    elif "favorite" in pat:
                        facts.append(f"User's favorite {fact}")
                    elif "like" in pat:
                        facts.append(f"User likes {fact}")
                    elif "am a" in pat:
                        facts.append(f"User is a {fact}")
                    elif "live in" in pat:
                        facts.append(f"User lives in {fact}")
                    elif "work as" in pat:
                        facts.append(f"User works as {fact}")
        return facts

    def clear_memory(self):
        """Clears all stored memories."""
        self.filepath.write_text("[]", encoding="utf-8")

# Global singleton instance
memory_store = MemoryStore()
