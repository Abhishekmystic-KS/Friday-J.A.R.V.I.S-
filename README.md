# J.A.R.V.I.S 

This is a voice assistant project with voice wake-word detection, STT, LLM, and TTS. It also includes a standalone RAG knowledge base chat window.

## Main Files

- [scripts/run_assistant.py](scripts/run_assistant.py) — run voice assistant
- [scripts/run_orb.py](scripts/run_orb.py) — run orb animation only
- [scripts/run_robo.py](scripts/run_robo.py) — run robo popup animation only
- [src/jarvis/assistant.py](src/jarvis/assistant.py) — assistant core logic
- [src/jarvis/ui/orb_popup.py](src/jarvis/ui/orb_popup.py) — orb animation UI
- [src/jarvis/ui/robo_popup.py](src/jarvis/ui/robo_popup.py) — robo popup launcher
- [src/jarvis/ui/chat_window.py](src/jarvis/ui/chat_window.py) — standalone RAG knowledge base chat window
- [config/app.json](config/app.json) — settings
- [env/.env](env/.env) — API keys

## Demo Video

<video src="https://github.com/Abhishekmystic-KS/Friday-J.A.R.V.I.S-/blob/e6d3583cf41e240720f0ac3365b8521492e0c4ed/assets/media/demo/demovideo.mp4" controls width="100%"></video>

## Quick Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install "setuptools<81"
```

### Optional: RAG Knowledge Base Chat

For the standalone chat window, install RAG dependencies:

```bash
pip install chromadb langchain-text-splitters requests
```

Then ingest your knowledge documents:

```bash
python RAG/ingestor.py --reset
python RAG/ingestors/github_ingestor.py  # Optional: fetch GitHub profiles
```

Add keys to [env/.env](env/.env):

```env
GROQ_API_KEY=your_groq_key_here
GITHUB_TOKEN=your_github_token_here  # Optional, for RAG GitHub integration
```

## Run

**Voice Assistant:**
```bash
python scripts/run_assistant.py
```

**Robo Popup:**
```bash
python scripts/run_robo.py
```

Then click the 💬 Chat button to open the separate RAG chat window.

## Voice Commands

- **Wake**: `friday`, `hey friday`, `wake up`
- **Sleep**: `go to sleep friday`
- **Chat**: Click the 💬 Chat button on the robo popup to open the separate knowledge base window

## Features

- **Speech-to-Text**: Groq Whisper (whisper-large-v3-turbo)
- **LLM**: Groq Llama 3.1-8b-instant with streaming
- **Text-to-Speech**: edge-tts (Microsoft) or espeak (offline, auto-selected based on speed)
- **Voice Activity Detection**: WebRTC VAD with 15-block silence threshold
- **UI**: Draggable orb and robo animations, plus a separate chat window
- **RAG**: Knowledge base chat with ChromaDB vector search + semantic similarity fallback

## Architecture

- **Streaming LLM-to-TTS**: LLM response streams → sentence-chunked → queued to TTS worker
- **Latency Logging**: Optional component-level timing instrumentation
- **Threading**: Non-blocking audio capture, LLM generation, TTS playback
- **Config-Driven**: Behavior toggles in [config/app.json](config/app.json)

## Notes

- Project is actively being developed
- Logs: [data/logs](data/logs)
- Knowledge base stored in: [RAG/store](RAG/store) (auto-generated)
- Animation frames cached in: [assets/media/animations/robo_frames_*](assets/media/animations)
