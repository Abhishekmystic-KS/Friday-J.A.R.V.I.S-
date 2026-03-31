import logging
import os
import re
import threading

from dotenv import dotenv_values
from groq import Groq

from jarvis.config import ROOT_DIR, load_config


def normalize_text(text):
    clean = (text or "").strip().lower()
    return re.sub(r"\s+", " ", clean)


def contains_any(text, phrases):
    for phrase in phrases:
        if phrase in text:
            return True
    return False


def setup_logger(log_file):
    path = ROOT_DIR / log_file
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("jarvis")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


def load_api_key():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        return key

    env_file = ROOT_DIR / "env" / ".env"
    if env_file.exists():
        key = (dotenv_values(env_file).get("GROQ_API_KEY") or "").strip()
        if key:
            return key

    raise RuntimeError("Missing GROQ_API_KEY in env/.env")


def start_hotkey(enabled, combo, event_obj):
    if not enabled:
        return None
    try:
        from pynput import keyboard

        def trigger():
            event_obj.set()
            print("[hotkey] pressed")

        listener = keyboard.GlobalHotKeys({combo: trigger})
        listener.start()
        print("Hotkey enabled:", combo)
        return listener
    except Exception as exc:
        print("Hotkey disabled:", exc)
        return None


def get_llm_response(client, llm_model, history, user_text, max_history):
    history.append({"role": "user", "content": user_text})
    try:
        out = client.chat.completions.create(
            model=llm_model,
            messages=history,
            max_tokens=120,
            temperature=0.7,
        )
        reply = (out.choices[0].message.content or "").strip()
    except Exception as exc:
        print("LLM error:", exc)
        reply = "Sorry, I could not process that."

    history.append({"role": "assistant", "content": reply})
    max_items = max(1, int(max_history))
    if len(history) > max_items + 1:
        history[:] = history[:1] + history[-max_items:]
    return reply


def run_assistant():
    cfg = load_config()
    logger = setup_logger(cfg["log_file"])

    wake_phrases = [str(x).lower() for x in cfg["wake_phrases"]]
    sleep_phrases = [str(x).lower() for x in cfg["sleep_phrases"]]
    max_history = int(cfg["max_history_messages"])

    api_key = load_api_key()
    client = Groq(api_key=api_key)

    hotkey_event = threading.Event()
    hotkey_listener = start_hotkey(
        bool(cfg.get("hotkey_enabled", False)),
        str(cfg.get("hotkey_combo", "<ctrl>+<alt>+j")),
        hotkey_event,
    )

    print("Assistant started (safe mode)")
    print("Type text and press Enter. Ctrl+C to stop.")

    history = [{"role": "system", "content": str(cfg["system_prompt"])}]
    is_awake = True

    try:
        while True:
            if hotkey_event.is_set():
                hotkey_event.clear()
                is_awake = True
                print("JARVIS: Hotkey received. I am ready.")

            text = input("You: ").strip()
            if not text:
                continue

            logger.info("user=%s", text)
            t = normalize_text(text)

            if contains_any(t, sleep_phrases):
                is_awake = False
                msg = "Going to sleep. Say friday or hey friday to wake me."
                print("JARVIS:", msg)
                logger.info("assistant=%s", msg)
                continue

            if not is_awake:
                if contains_any(t, wake_phrases):
                    is_awake = True
                    msg = "I am awake. How can I help?"
                    print("JARVIS:", msg)
                    logger.info("assistant=%s", msg)
                continue

            if contains_any(t, wake_phrases):
                msg = "I am here. How can I help?"
                print("JARVIS:", msg)
                logger.info("assistant=%s", msg)
                continue

            response = get_llm_response(client, str(cfg["llm_model"]), history, text, max_history)
            print("JARVIS:", response)
            logger.info("assistant=%s", response)
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        if hotkey_listener:
            try:
                hotkey_listener.stop()
            except Exception:
                pass


def main():
    run_assistant()


if __name__ == "__main__":
    main()
