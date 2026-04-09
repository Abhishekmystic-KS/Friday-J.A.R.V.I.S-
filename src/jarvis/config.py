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
    "agent_enabled": False,
    "agent_phase": 1,
    "intent_classifier_mode": "hybrid",
    "intent_classifier_model": "llama-3.1-8b-instant",
    "intent_logging_enabled": True,
    "agent_max_steps": 4,
    "agent_replan_enabled": True,
    "agent_use_llm_planner": True,
    "agent_memory_enabled": True,
    "agent_memory_file": "data/memory/agent_memory.jsonl",
    "log_file": "data/logs/conversation.log",
    "voice_ux_barge_in_enabled": True,
    "voice_ux_confidence_threshold": 0.55,
    "voice_ux_clarification_on_low_confidence": True,
    "voice_ux_response_max_lines": 2,
    "voice_ux_metrics_enabled": False,
    "voice_ux_filler_patterns": ["uh", "um", "er", "erm", "hmm", "huh", "yeah", "yep", "nope", "ok", "okay", "gotcha", "sure", "right", "what", "huh"],
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
