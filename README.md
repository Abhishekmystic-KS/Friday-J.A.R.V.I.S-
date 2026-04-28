# J.A.R.V.I.S

A voice assistant with wake-word detection, STT, LLM, TTS, an agentic layer, a RAG knowledge base, and live web search.

## Demo Video

[▶ Watch Demo Video](https://github.com/Abhishekmystic-KS/Friday-J.A.R.V.I.S-/raw/refs/heads/main/assets/media/demo/demovideo.mp4)

## Workflow

![Friday J.A.R.V.I.S Workflow](https://github.com/user-attachments/assets/fd3f0484-0251-4d0f-9f2a-3b01aca6f17c)

## Quick Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install sentence-transformers chromadb langchain-text-splitters
pip install "setuptools<81"
# Optional: Scrapling for stealthy web search
pip install "scrapling[ai]" && scrapling install
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
- **Text-to-Speech**: edge-tts (Microsoft) auto-benchmarked at startup; optional Groq TTS (Orpheus)
- **Voice Activity Detection**: WebRTC VAD
- **Agent (Phase 2)**: multi-step planner with intent classification, replanning, LLM planner, and persistent memory
- **Web Search**: Scrapling (stealthy) → DuckDuckGo API → Google News RSS — multi-tier fallback
- **Memory Tools**: `memory_save` and `memory_recall` tools for long-term facts
- **Intent Classifier**: keyword, LLM, or hybrid mode
- **Hotkey**: optional global keyboard shortcut to activate Jarvis
- **Voice UX**: barge-in, confidence threshold, filler-word filtering, clarification prompts
- **UI**: Draggable orb and robo popup animations

## Web Search

The web search tool uses a three-tier fallback strategy:

1. **Scrapling** (primary) — stealthy browser-like fetcher that bypasses basic bot detection
2. **DuckDuckGo Instant Answer API** — lightweight fallback when Scrapling is unavailable or times out
3. **Google News RSS** — used first for news/headline queries; also as a last-resort fallback

News-like queries (containing keywords like *news*, *latest*, *today*, *headline*) skip straight to the Google News RSS feed for fresher results.

See [`docs/integrations/SCRAPLING_INTEGRATION.md`](docs/integrations/SCRAPLING_INTEGRATION.md) for full details.

## Agent Tools

| Tool | Description |
|------|-------------|
| `get_time` | Returns the current date and time |
| `calculator` | Evaluates a math expression safely |
| `open_app` | Launches Chrome, Firefox, Spotify, Terminal, or Files |
| `web_search` | Multi-tier web search (Scrapling / DDG / News RSS) |
| `memory_save` | Persists a fact to long-term memory |
| `memory_recall` | Retrieves relevant facts from long-term memory |

## Key Config (`config/app.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `llm_model` | `llama-3.1-8b-instant` | Groq LLM model |
| `stt_model` | `whisper-large-v3-turbo` | Groq STT model |
| `tts_provider` | `edge` | TTS backend (`edge` or `groq`) |
| `tts_voice` | `en-US-AriaNeural` | edge-tts voice |
| `tts_groq_enabled` | `false` | Enable Groq TTS (Orpheus) |
| `tts_groq_model` | `canopylabs/orpheus-v1-english` | Groq TTS model |
| `tts_groq_voice` | `troy` | Groq TTS voice |
| `agent_enabled` | `true` | Enable agentic layer |
| `agent_phase` | `2` | Agent phase (1 = basic, 2 = replanning) |
| `agent_memory_enabled` | `true` | Persist agent memory |
| `agent_max_steps` | `4` | Max agent plan steps |
| `agent_replan_enabled` | `true` | Allow agent to replan on failure |
| `agent_use_llm_planner` | `false` | Use LLM-generated plans instead of keyword planner |
| `intent_classifier_mode` | `keyword` | Intent mode: `keyword`, `llm`, or `hybrid` |
| `intent_classifier_model` | `llama-3.1-8b-instant` | Model for LLM-based intent classification |
| `web_search_provider` | `auto` | `auto`, `scrapling`, or `duckduckgo` |
| `web_search_scrapling_enabled` | `true` | Enable Scrapling for web search |
| `web_search_timeout` | `8` | Web fetch timeout in seconds |
| `hotkey_enabled` | `false` | Enable global hotkey to activate Jarvis |
| `hotkey_combo` | `<ctrl>+<alt>+j` | Hotkey key combination |
| `voice_ux_barge_in_enabled` | `true` | Allow interrupting playback |
| `voice_ux_confidence_threshold` | `0.55` | Minimum STT confidence to act on |
| `voice_ux_clarification_on_low_confidence` | `true` | Ask for clarification on low-confidence input |
| `latency_logging_enabled` | `false` | Log per-component timing |
| `denoise_enabled` | `false` | Enable microphone noise reduction |

## Notes

- Logs: `data/logs/`
- Agent memory: `data/memory/agent_memory.jsonl`
- Animation frames cached in: `assets/media/animations/`
- Project is actively being developed

## Authors

- **Abhishekmystic-KS** — [github.com/Abhishekmystic-KS](https://github.com/Abhishekmystic-KS) — Original Author
- **AkshathaaRk** — [github.com/AkshathaaRk](https://github.com/AkshathaaRk) — Co-Developer
