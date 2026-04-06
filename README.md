# J.A.R.V.I.S 

This is a voice assistant project in progress.


## Main files

- [scripts/run_assistant.py](scripts/run_assistant.py) — run assistant
- [scripts/run_orb.py](scripts/run_orb.py) — run orb only
- [src/jarvis/assistant.py](src/jarvis/assistant.py) — assistant logic
- [src/jarvis/ui/orb_popup.py](src/jarvis/ui/orb_popup.py) — UI
- [config/app.json](config/app.json) — settings
- [env/.env](env/.env) — API key

## Demo Video
[![Demo](./readmeui/preview.gif)](./readmeui/demovideo.mp4)
<video src="https://raw.githubusercontent.com/Abhishekmystic-KS/Friday-J.A.R.V.I.S-/db326c0586b9412a7d377337528fd355cc3d538f/readmeui/demovideo.mp4" controls="controls" muted="muted" style="max-width: 100%;"></video>

## Quick setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install "setuptools<81"
```

Add key to [env/.env](env/.env):

```env
GROQ_API_KEY=your_groq_key_here
```

## Run

```bash
python scripts/run_assistant.py
```

## Basic voice commands

- Wake: `friday`, `hey friday`, `wake up`
- Sleep: `go to sleep friday`

## Notes

- Project is still being improved.
- Logs: [data/logs](data/logs)

Current goal:
- listen from mic
- wake/sleep by voice
- transcribe with Groq
- reply with LLM + TTS
- show orb popup UI

## Main files

- [scripts/run_assistant.py](scripts/run_assistant.py) — run assistant
- [scripts/run_orb.py](scripts/run_orb.py) — run orb only
- [src/jarvis/assistant.py](src/jarvis/assistant.py) — assistant logic
- [src/jarvis/ui/orb_popup.py](src/jarvis/ui/orb_popup.py) — UI
- [config/app.json](config/app.json) — settings
- [env/.env](env/.env) — API key

## Quick setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install groq python-dotenv sounddevice soundfile numpy webrtcvad noisereduce edge-tts pynput
pip install "setuptools<81"
```

Add key to [env/.env](env/.env):

```env
GROQ_API_KEY=your_groq_key_here
```

## Run

```bash
python scripts/run_assistant.py
```

## Basic voice commands

- Wake: `friday`, `hey friday`, `wake up`
- Sleep: `go to sleep friday`

## Notes

- Project is still being improved.
- Logs: [data/logs](data/logs)
