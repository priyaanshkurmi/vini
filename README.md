# VINI — Embodied Emotional AI Desktop Agent

A modular, voice-enabled, emotionally-aware agentic system that lives
persistently on the desktop. Built as a portfolio project to demonstrate
advanced system architecture, LLM orchestration, RAG, and state modeling.

---

## What It Does

- 🎤 **Listens** to your voice via Whisper STT
- 🧠 **Thinks** using a pluggable LLM (Google Gemini or local Ollama)
- 💾 **Remembers** using ChromaDB vector RAG + SQLite long-term memory
- 💙 **Feels** via a mathematical emotion state model with exponential decay
- 🛠️ **Acts** with sandboxed OS tool execution (open apps, read/write files)
- 👤 **Embodies** as a holographic avatar overlay via Electron + Three.js

---

## Architecture
```
┌─────────────────────────────────────────────────────┐
│                   VINI System                        │
├──────────────┬──────────────┬───────────────────────┤
│ Avatar Layer │ Voice Layer  │    Backend Layer       │
│ Electron     │ Whisper STT  │    FastAPI (async)     │
│ Three.js     │ Piper TTS    │    WebSocket + REST    │
│ WebGL/GLSL   │              │                        │
├──────────────┴──────────────┼───────────────────────┤
│          LLM Service        │    Memory Engine       │
│  Gemini 2.0 Flash / Ollama  │  ChromaDB (vector)     │
│  Abstract Base Class        │  SQLite (structured)   │
│  Adapter Pattern            │  In-memory buffer      │
├─────────────────────────────┼───────────────────────┤
│       Emotion Engine        │    Tool Executor       │
│  4D state vector + decay    │  Whitelisted OS cmds   │
│  Event-driven deltas        │  Audit logging         │
└─────────────────────────────┴───────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| LLM | Google Gemini 2.0 Flash / Ollama llama3 |
| Memory | ChromaDB, sentence-transformers, SQLite |
| Voice | OpenAI Whisper, Piper TTS |
| Avatar | Electron, Three.js, WebGL, GLSL shaders |
| Protocol | REST + WebSocket |

---

## Quick Start

**Prerequisites:** Python 3.11, Node.js 20+, Ollama
```bash
# Clone
git clone https://github.com/yourusername/vini.git
cd vini

# Install backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Gemini API key

# Install avatar
cd ../avatar
npm install

# Launch everything
cd ..
./start_vini.sh
```

---

## Key Technical Decisions

**Pluggable LLM (Adapter Pattern)**
The LLM service uses an Abstract Base Class. Switching between Gemini and
Ollama requires changing one environment variable — zero code changes.

**Dual Memory System**
ChromaDB stores vector embeddings for semantic RAG retrieval. SQLite stores
structured facts. Every query retrieves top-5 semantically similar memories
and injects them into the prompt.

**Emotion Engine**
A 4-dimensional state vector (happiness, trust, energy, attachment) decays
exponentially toward a neutral baseline over time. Events trigger delta
shifts. The state conditions every LLM prompt and drives avatar shaders.

**Safety-First Tool Execution**
Three independent safety mechanisms: static app/directory whitelist,
human-in-the-loop confirmation for destructive operations, append-only
audit log of every tool invocation.

---

## Project Structure
```
vini/
├── backend/
│   ├── api/          # FastAPI routes + WebSocket
│   ├── services/     # LLM providers, TTS, STT, prompt builder
│   ├── memory/       # ChromaDB vector store + SQLite
│   ├── emotion/      # Emotion state engine
│   └── tools/        # Tool registry, detector, executor
├── avatar/
│   └── src/          # Electron + Three.js hologram renderer
├── logs/             # Runtime logs (gitignored)
├── start_vini.sh     # One-command launcher
└── stop_vini.sh      # Graceful shutdown
```

---

## Demo

> 📹 Demo video — [link coming soon]

---

*Built in 5 weeks. Solo development.*
```

---

## File 4 — .env.example
```
code ~/vini/backend/.env.example
```

Paste and save — this is the safe version without real keys that goes into Git:
```
# LLM — set LLM_PROVIDER to 'gemini' or 'ollama'
LLM_PROVIDER=ollama
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Memory
DB_URL=sqlite:///vini.db
CHROMA_PATH=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Voice
WHISPER_MODEL=base
TTS_MODEL=models/tts/en_US-lessac-medium.onnx

# System
WS_PORT=8000
LOG_LEVEL=INFO
TOOL_AUDIT_LOG=tool_audit.log
```

---