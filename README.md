# J.A.R.V.I.S

A voice assistant with wake-word detection, STT, LLM, TTS, an agentic layer, and a RAG knowledge base.

## Demo Video

[▶ Watch Demo Video](https://github.com/Abhishekmystic-KS/Friday-J.A.R.V.I.S-/raw/refs/heads/main/assets/media/demo/demovideo.mp4)

## Quick Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install sentence-transformers chromadb langchain-text-splitters
pip install "setuptools<81"
```

Add your API key to `env/.env`:
```
GROQ_API_KEY=your_key_here
```

## Run

**Voice Assistant:**
```bash
python scripts/run_assistant.py
```

**Robo Popup (animation only):**
```bash
python scripts/run_robo.py
```

**Orb Popup (animation only):**
```bash
python scripts/run_orb.py
```

**Benchmark TTS latency:**
```bash
python scripts/benchmark_tts.py
```

## RAG Knowledge Base

Drop `.md` files into `RAG/knowledge/`, then ingest them:

```bash
# First-time or after adding new files
python RAG/ingestor.py

# Reset and re-ingest
python RAG/ingestor.py --reset
```

- **Embedder**: `all-MiniLM-L6-v2` via SentenceTransformers (22 MB, CPU-only)
- **Store**: ChromaDB persisted to `RAG/store/`
- **Retriever**: semantic search over the knowledge base at query time

## Voice Commands

- **Wake**: `friday`, `hey friday`, `wake up`
- **Sleep**: `go to sleep friday`, `sleep friday`, `friday go to sleep`

## Features

- **Speech-to-Text**: Groq Whisper (whisper-large-v3-turbo)
- **LLM**: Groq Llama 3.1-8b-instant with streaming
- **Text-to-Speech**: edge-tts (Microsoft) — auto-benchmarked at startup
- **Voice Activity Detection**: WebRTC VAD
- **Agent**: multi-step planner with intent classification, memory, and replanning (phase 2)
- **Voice UX**: barge-in, confidence threshold, filler-word filtering, clarification prompts
- **UI**: Draggable orb and robo popup animations

## Key Config (`config/app.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `llm_model` | `llama-3.1-8b-instant` | Groq LLM model |
| `stt_model` | `whisper-large-v3-turbo` | Groq STT model |
| `tts_provider` | `edge` | TTS backend |
| `tts_voice` | `en-US-AriaNeural` | TTS voice |
| `agent_enabled` | `true` | Enable agentic layer |
| `agent_memory_enabled` | `true` | Persist agent memory |
| `agent_max_steps` | `4` | Max agent plan steps |
| `voice_ux_barge_in_enabled` | `true` | Allow interrupting playback |
| `latency_logging_enabled` | `false` | Log per-component timing |

## Notes

- Logs: `data/logs/`
- Agent memory: `data/memory/agent_memory.jsonl`
- Animation frames cached in: `assets/media/animations/`
- Project is actively being developed
