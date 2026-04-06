from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "app.json"

DEFAULT_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "stt_model": "whisper-large-v3-turbo",
    "llm_provider": "groq",
    "llm_model": "llama-3.1-8b-instant",
    "bytez_model": "openai/gpt-4o",
    "wake_phrases": ["friday", "hey friday", "wake up"],
    "sleep_phrases": ["go to sleep friday", "sleep friday", "friday go to sleep"],
    "wake_cooldown_seconds": 15,
    "max_history_messages": 12,
    "tts_voice": "en-US-AriaNeural",
    "tts_provider": "auto",
    "tts_benchmark_text": "System ready. This is a latency check.",
    "latency_logging_enabled": False,
    "denoise_enabled": False,
    "system_prompt": "You are Jarvis, a witty AI assistant. Keep responses short and punchy (1-2 sentences).",
    "hotkey_enabled": False,
    "hotkey_combo": "<ctrl>+<alt>+j",
    "log_file": "data/logs/conversation.log",
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            user_cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(user_cfg, dict):
                cfg.update(user_cfg)
        except Exception:
            pass
    else:
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return cfg
