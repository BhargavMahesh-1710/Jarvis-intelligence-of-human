# MAHI JARVIS — Advanced Personal AI Assistant

An agentic AI assistant engineered according to the **MAHI JARVIS Project Blueprint**.

JARVIS is designed as an AI-agent system rather than a simple chatbot: it listens, understands, reasons, remembers, retrieves knowledge, uses tools, analyzes visual input, speaks naturally, and safely executes approved digital actions.

---

## 🌟 Key Architecture & Features

1. **FastAPI Backend (`backend/`)**:
   - Asynchronous Python backend with clean modular design.
   - Core endpoints: `/health`, `/chat`, `/chat/confirm`, `/voice/stt`, `/voice/tts`, `/vision/analyze`.

2. **Core Algorithms**:
   - **Algorithm A (Intent & Tool Routing)**: Classifies input into `chat`, `search`, `calculator`, `memory`, `document` (RAG), or `action`.
   - **Algorithm B (RAG Retrieval)**: Ingests documents from `data/knowledge/`, chunks them, fits TF-IDF vector embeddings, and performs cosine similarity search.
   - **Algorithm C (Agent Planning)**: Breaks complex goals into actionable tool steps.
   - **Algorithm D (Long-Term Memory)**: Automatically extracts stable personal preferences and facts, persists them in `data/memory.json`, and injects relevant context into future queries.

3. **Safety & Permission Layer (`core/safety.py`)**:
   - Strictly segregates read-only operations from consequential operations (such as deleting files or destructive actions).
   - Consequential actions generate a pending approval token that requires explicit user confirmation via the UI before execution.
   - Comprehensive audit logging.

4. **Extensible Tool Registry (`tools/`)**:
   - **AST Math Calculator**: Safe mathematical expression evaluation.
   - **Web Search**: DuckDuckGo web search integration.
   - **Workspace Files**: Sandboxed file read, write, list, and delete operations.
   - **Browser/URL Reader**: Webpage fetching and HTML-to-text extraction.

5. **Futuristic Holographic HUD (`frontend/`)**:
   - Iconic Iron Man Arc Reactor with rotating energetic concentric rings.
   - Real-time soundwave voice visualizer.
   - Web Speech API integration for live Speech-to-Text (STT) and Natural Speech Synthesis (TTS).
   - Interactive Consequential Action Confirmation modal cards.
   - Multimodal Optical Vision panel for image/camera analysis.
   - Memory and RAG Knowledge manager drawer.

---

## 🚀 Quick Start

### 1. Prerequisites & Dependencies
Ensure Python 3.10+ is installed. Install requirements:
```bash
pip install -r backend/requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional: Add your `GEMINI_API_KEY` or `OPENAI_API_KEY`. If left blank, JARVIS operates automatically using its built-in offline intelligent engine!)*

### 3. Start the JARVIS Server
```bash
python backend/main.py
```
Or with uvicorn:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Access the Holographic Interface
Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🧪 Running Automated Tests
Run the test suite to verify all core components:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📁 Project Structure

```
mahi-jarvis/
├── backend/
│   ├── main.py              # FastAPI server entry point & static mount
│   ├── config.py            # Environment and path configurations
│   ├── requirements.txt     # Python dependencies
│   ├── routes/
│   │   ├── chat.py          # /chat, /chat/confirm, memory & RAG APIs
│   │   ├── voice.py         # /voice/stt & /voice/tts endpoints
│   │   └── vision.py        # /vision/analyze multimodal endpoint
│   ├── core/
│   │   ├── agent.py         # Routing, planning, LLM synthesis
│   │   ├── memory.py        # Long-term memory store & extraction
│   │   ├── rag.py           # Document chunking, vector DB & search
│   │   └── safety.py        # Permission and confirmation layer
│   ├── tools/
│   │   ├── calculator.py    # Math evaluation tool
│   │   ├── web_search.py    # DuckDuckGo search integration
│   │   ├── files.py         # Safe workspace file operations
│   │   └── browser.py       # URL text inspector
│   └── data/
│       └── knowledge/       # RAG knowledge files (e.g. jarvis_manual.md)
├── frontend/
│   ├── index.html           # Futuristic JARVIS HUD interface
│   ├── style.css            # Sci-fi styling, Arc Reactor, visualizer
│   └── app.js               # Voice I/O, API client, modal controllers
├── tests/
│   └── test_jarvis.py       # Full system test suite
├── .gitignore
├── .env.example
└── README.md
```
