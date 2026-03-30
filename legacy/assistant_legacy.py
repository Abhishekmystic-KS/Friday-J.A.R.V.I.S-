import os
import re
import json
import logging
import uuid
import shutil
import subprocess
import sys
import tempfile
import time
import asyncio
import threading
from pathlib import Path

import sounddevice as sd
import soundfile as sf
import numpy as np
import webrtcvad
from noisereduce import reduce_noise
from dotenv import dotenv_values
from groq import Groq
import edge_tts

VOICE_UI_DIR = Path(__file__).resolve().parent
ENV_FILE = VOICE_UI_DIR / "env" / ".env"
CONFIG_FILE = VOICE_UI_DIR / "config.json"
LOGS_DIR = VOICE_UI_DIR / "logs"

DEFAULT_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "record_seconds": 3,
    "stt_model": "whisper-large-v3-turbo",
    "llm_model": "llama-3.1-8b-instant",
    "wake_phrases": ["friday", "hey friday", "wake up"],
    "sleep_phrases": ["go to sleep friday", "sleep friday", "friday go to sleep"],
    "wake_cooldown_seconds": 15,
    "max_history_messages": 12,
    "tts_voice": "en-US-AriaNeural",
    "system_prompt": "You are Jarvis, a witty AI assistant. Keep responses short and punchy (1-2 sentences).",
    "hotkey_enabled": True,
    "hotkey_combo": "<ctrl>+<alt>+j",
    "log_file": "logs/conversation.log",
    "memory_enabled": True,
    "memory_db_path": "memory/chroma",
    "memory_collection": "jarvis_memory",
    "memory_top_k": 3,
}

HOTKEY_SIGNAL = "__HOTKEY_TRIGGERED__"

# Runtime settings (defaults, can be overridden from config in main)
SAMPLE_RATE = DEFAULT_CONFIG["sample_rate"]
CHANNELS = DEFAULT_CONFIG["channels"]
RECORD_SECONDS = DEFAULT_CONFIG["record_seconds"]
MODEL_NAME = DEFAULT_CONFIG["stt_model"]
LLM_MODEL = DEFAULT_CONFIG["llm_model"]
WAKE_PHRASES = list(DEFAULT_CONFIG["wake_phrases"])
SLEEP_PHRASES = list(DEFAULT_CONFIG["sleep_phrases"])
WAKE_COOLDOWN_SECONDS = DEFAULT_CONFIG["wake_cooldown_seconds"]
MAX_HISTORY_MESSAGES = DEFAULT_CONFIG["max_history_messages"]
TTS_VOICE = DEFAULT_CONFIG["tts_voice"]
SYSTEM_PROMPT = DEFAULT_CONFIG["system_prompt"]


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            user_cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(user_cfg, dict):
                cfg.update(user_cfg)
        except Exception as e:
            print(f"Config warning: {e}. Using defaults.")
    else:
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return cfg


def setup_logger(log_file: str) -> logging.Logger:
    log_path = VOICE_UI_DIR / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("jarvis")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def init_memory_store(cfg: dict, logger: logging.Logger):
    if not bool(cfg.get("memory_enabled", True)):
        return None
    try:
        import chromadb

        db_path = VOICE_UI_DIR / str(cfg.get("memory_db_path", "memory/chroma"))
        db_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(db_path))
        collection = client.get_or_create_collection(name=str(cfg.get("memory_collection", "jarvis_memory")))
        logger.info("memory_store_initialized path=%s", db_path)
        return collection
    except Exception as e:
        logger.exception("memory_store_init_failed")
        print(f"Memory disabled: {e}")
        return None


def is_memory_store_command(text: str) -> bool:
    t = normalize_text(text)
    return (
        t.startswith("remember ")
        or " remember " in f" {t} "
        or "can you remember" in t
    )


def extract_memory_text(text: str) -> str:
    t = normalize_text(text)
    # Remove common lead-ins while preserving actual content.
    patterns = [
        r"^remember\s+(important|this)?\s*[:,-]?\s*",
        r"^can you remember\s+",
        r"^please remember\s+",
        r"^i said remember\s+",
    ]
    cleaned = t
    for p in patterns:
        cleaned = re.sub(p, "", cleaned).strip()

    # If nothing useful left, don't store.
    if not cleaned or cleaned in {"name", "my name"}:
        return ""
    return cleaned


def is_memory_recall_command(text: str) -> bool:
    t = normalize_text(text)
    phrases = [
        "what do you remember",
        "what did i ask you to remember",
        "recall memory",
        "show memory",
        "what is my name",
        "tell me my name",
        "can you tell me the name that i said",
        "what did i tell you earlier",
        "do you remember my",
    ]
    return any(p in t for p in phrases)


def remember_important(collection, memory_text: str, logger: logging.Logger) -> bool:
    if not collection or not memory_text:
        return False
    try:
        memory_id = f"mem_{uuid.uuid4().hex}"
        collection.add(
            ids=[memory_id],
            documents=[memory_text],
            metadatas=[{"type": "important", "ts": int(time.time())}],
        )
        logger.info("memory_saved id=%s text=%s", memory_id, memory_text)
        return True
    except Exception:
        logger.exception("memory_save_failed")
        return False


def retrieve_memory_context(collection, query_text: str, top_k: int = 3) -> list[str]:
    if not collection:
        return []
    try:
        results = collection.query(query_texts=[query_text], n_results=top_k)
        docs = (results.get("documents") or [[]])[0]
        return [d for d in docs if isinstance(d, str) and d.strip()]
    except Exception:
        return []


def start_hotkey_listener(enabled: bool, combo: str, trigger_event: threading.Event):
    if not enabled:
        return None
    try:
        from pynput import keyboard

        def on_activate():
            trigger_event.set()
            print("⌨️ Hotkey pressed.")

        listener = keyboard.GlobalHotKeys({combo: on_activate})
        listener.start()
        print(f"Hotkey enabled: {combo}")
        return listener
    except Exception as e:
        print(f"Hotkey disabled: {e}")
        return None


def load_api_key() -> str:
    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    if ENV_FILE.exists():
        env_data = dotenv_values(ENV_FILE)
        key = (env_data.get("GROQ_API_KEY") or "").strip()
        if key:
            return key

    raise RuntimeError(
        f"Missing GROQ_API_KEY. Add it to {ENV_FILE} or export GROQ_API_KEY in shell."
    )


def play_start_sound() -> None:
    sound_file = VOICE_UI_DIR / "assets" / "starting_voice.mp3"
    if not sound_file.exists():
        return

    players = [
        ["mpg123", "-q", str(sound_file)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(sound_file)],
        ["paplay", str(sound_file)],
    ]

    for cmd in players:
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue


def speak(text: str) -> None:
    """Convert text to speech using edge-tts and play it."""
    try:
        print(f"🔊 Speaking: {text}")
        with tempfile.NamedTemporaryFile(prefix="jarvis_tts_", suffix=".mp3", delete=False) as tmp:
            audio_file = tmp.name

        async def _synthesize() -> None:
            communicator = edge_tts.Communicate(text=text, voice=TTS_VOICE)
            await communicator.save(audio_file)

        asyncio.run(_synthesize())
        print(f"✓ TTS saved to {audio_file}")
        
        # Play using available player
        players = [
            ["mpg123", "-q", audio_file],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file],
            ["paplay", audio_file],
        ]
        
        for cmd in players:
            if shutil.which(cmd[0]):
                print(f"Playing with {cmd[0]}...")
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                    print("✓ Audio played.")
                    return
                except Exception as e:
                    print(f"Error with {cmd[0]}: {e}")
                    continue
        
        print("⚠ No audio player found")
    except Exception as e:
        print(f"❌ TTS error: {e}")


def launch_orb() -> None:
    script = VOICE_UI_DIR / "jarvis_orb_popup.py"
    if script.exists():
        subprocess.Popen([sys.executable, str(script)])


def record_audio_wav(seconds: int = RECORD_SECONDS) -> str:
    print(f"Recording for {seconds} seconds...")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()

    with tempfile.NamedTemporaryFile(prefix="jarvis_", suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, audio, SAMPLE_RATE)
        return tmp.name


def record_with_vad(hotkey_event: threading.Event | None = None) -> str:
    """Record audio using Voice Activity Detection (VAD) - stops when silence detected."""
    vad = webrtcvad.Vad(3)  # 3 = aggressive, 0 = less aggressive
    
    frames = []
    silent_frames = 0
    max_silent_frames = 15  # ~375ms of silence triggers stop
    
    print("🎤 Listening for voice...")
    
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=int(SAMPLE_RATE * 0.02),  # 20ms chunks
            dtype="float32"
        ) as stream:
            while True:
                if hotkey_event and hotkey_event.is_set():
                    hotkey_event.clear()
                    return HOTKEY_SIGNAL

                audio_chunk, _ = stream.read(int(SAMPLE_RATE * 0.02))
                
                # Convert to 16-bit PCM for VAD
                pcm_chunk = (audio_chunk * 32767).astype("int16")
                
                is_speech = vad.is_speech(pcm_chunk.tobytes(), SAMPLE_RATE)
                
                if is_speech:
                    frames.append(audio_chunk)
                    silent_frames = 0
                else:
                    if frames:  # Only count silence after speech has been detected
                        silent_frames += 1
                        frames.append(audio_chunk)  # Include some trailing silence
                    
                    if silent_frames > max_silent_frames:
                        break
    except Exception as e:
        print(f"Recording error: {e}")
    
    if frames:
        audio = np.vstack(frames)
        
        with tempfile.NamedTemporaryFile(prefix="jarvis_vad_", suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio, SAMPLE_RATE)
            return tmp.name
    
    return None


def denoise_audio(wav_path: str) -> str:
    """Remove background noise from audio file."""
    try:
        audio, sr = sf.read(wav_path)
        
        # Reduce noise
        denoised = reduce_noise(y=audio, sr=sr)
        
        with tempfile.NamedTemporaryFile(prefix="jarvis_denoised_", suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, denoised, sr)
            return tmp.name
    except Exception as e:
        print(f"Denoising error: {e}")
        return wav_path  # Return original if denoising fails


def transcribe_wav(client: Groq, wav_path: str) -> str:
    with open(wav_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            file=audio_file,
            model=MODEL_NAME,
            language="en",
            temperature=0,
        )
    return (getattr(result, "text", "") or "").strip()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def contains_any_phrase(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def is_wake_phrase(text: str) -> bool:
    return contains_any_phrase(normalize_text(text), WAKE_PHRASES)


def is_sleep_command(text: str) -> bool:
    return contains_any_phrase(normalize_text(text), SLEEP_PHRASES)


def detect_intent(text: str) -> str:
    t = normalize_text(text)
    if any(kw in t for kw in ["open chrome", "open browser", "open firefox", "open terminal", "open files", "open file manager"]):
        return "system_command"
    return "question_or_chat"


def handle_system_command(text: str) -> str:
    t = normalize_text(text)
    try:
        if "open chrome" in t:
            if shutil.which("google-chrome"):
                subprocess.Popen(["google-chrome"])
                return "Opening Chrome."
            return "Chrome is not installed on this system."

        if "open browser" in t or "open firefox" in t:
            if shutil.which("firefox"):
                subprocess.Popen(["firefox"])
                return "Opening Firefox."
            subprocess.Popen(["xdg-open", "https://www.google.com"])
            return "Opening your default browser."

        if "open terminal" in t:
            if shutil.which("x-terminal-emulator"):
                subprocess.Popen(["x-terminal-emulator"])
                return "Opening terminal."
            if shutil.which("gnome-terminal"):
                subprocess.Popen(["gnome-terminal"])
                return "Opening terminal."
            return "I could not find a terminal app to open."

        if "open files" in t or "open file manager" in t:
            subprocess.Popen(["xdg-open", str(VOICE_UI_DIR)])
            return "Opening file manager."
    except Exception as e:
        return f"I couldn't run that command: {e}"

    return "I heard a command, but I don't support that one yet."


def get_llm_response(client: Groq, history: list[dict], user_text: str, memory_context: list[str] | None = None) -> str:
    """Get intelligent response from Groq LLM with conversation memory."""
    try:
        print("🤖 Thinking...")
        composed_user_text = user_text
        if memory_context:
            mem_block = "\n".join(f"- {m}" for m in memory_context)
            composed_user_text = (
                "Use the following relevant remembered facts if useful:\n"
                f"{mem_block}\n\n"
                f"User message: {user_text}"
            )

        history.append({"role": "user", "content": composed_user_text})
        response = client.chat.completions.create(
            messages=history,
            model=LLM_MODEL,
            max_tokens=100,
            temperature=0.7,
        )
        assistant_text = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": assistant_text})

        # Keep memory bounded (preserve system prompt + latest turns)
        if len(history) > (MAX_HISTORY_MESSAGES + 1):
            del history[1: len(history) - MAX_HISTORY_MESSAGES]

        return assistant_text
    except Exception as e:
        print(f"LLM error: {e}")
        return "Sorry, I couldn't process that."


def main() -> None:
    global SAMPLE_RATE, CHANNELS, RECORD_SECONDS, MODEL_NAME, LLM_MODEL
    global WAKE_PHRASES, SLEEP_PHRASES, WAKE_COOLDOWN_SECONDS
    global MAX_HISTORY_MESSAGES, TTS_VOICE, SYSTEM_PROMPT

    cfg = load_config()
    SAMPLE_RATE = int(cfg["sample_rate"])
    CHANNELS = int(cfg["channels"])
    RECORD_SECONDS = int(cfg["record_seconds"])
    MODEL_NAME = str(cfg["stt_model"])
    LLM_MODEL = str(cfg["llm_model"])
    WAKE_PHRASES = [str(x).lower() for x in cfg["wake_phrases"]]
    SLEEP_PHRASES = [str(x).lower() for x in cfg["sleep_phrases"]]
    WAKE_COOLDOWN_SECONDS = int(cfg["wake_cooldown_seconds"])
    MAX_HISTORY_MESSAGES = int(cfg["max_history_messages"])
    TTS_VOICE = str(cfg["tts_voice"])
    SYSTEM_PROMPT = str(cfg["system_prompt"])

    logger = setup_logger(str(cfg["log_file"]))
    hotkey_event = threading.Event()
    hotkey_listener = start_hotkey_listener(bool(cfg["hotkey_enabled"]), str(cfg["hotkey_combo"]), hotkey_event)
    memory_collection = init_memory_store(cfg, logger)
    memory_top_k = int(cfg.get("memory_top_k", 3))

    key = load_api_key()
    client = Groq(api_key=key)

    print("Groq voice is active.")
    print("Continuous listening started.")
    print(f"Wake words: {', '.join(WAKE_PHRASES)}")
    print(f"Sleep phrases: {', '.join(SLEEP_PHRASES)}")
    print("Press Ctrl+C to stop.\n")
    logger.info("assistant_started")

    last_wake_ts = 0.0
    is_awake = True
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    try:
        while True:
            wav_file = None
            denoised_file = None
            try:
                wav_file = record_with_vad(hotkey_event=hotkey_event)

                if wav_file == HOTKEY_SIGNAL:
                    is_awake = True
                    play_start_sound()
                    speak("Hotkey received. I'm ready.")
                    launch_orb()
                    last_wake_ts = time.time()
                    logger.info("event=hotkey_activated")
                    continue
                
                if not wav_file:
                    continue
                
                denoised_file = denoise_audio(wav_file)
                text = transcribe_wav(client, denoised_file).strip()

                if not text:
                    continue

                print(f"You said: {text}")
                logger.info("user=%s", text)
                now = time.time()

                if is_sleep_command(text):
                    is_awake = False
                    response = "Going to sleep. Say friday, hey friday, or wake up to wake me."
                    print(f"JARVIS: {response}\n")
                    speak(response)
                    logger.info("assistant=%s", response)
                    continue

                if is_memory_store_command(text):
                    memory_text = extract_memory_text(text)
                    if not memory_text:
                        response = "Tell me what to remember, for example: remember my name is Abhi."
                    elif remember_important(memory_collection, memory_text, logger):
                        response = "Got it. I saved that to long-term memory."
                    else:
                        response = "I couldn't save that memory."
                    print(f"JARVIS: {response}\n")
                    speak(response)
                    logger.info("assistant=%s", response)
                    continue

                if is_memory_recall_command(text):
                    mems = retrieve_memory_context(memory_collection, text, top_k=memory_top_k)
                    if mems:
                        response = "Here is what I remember: " + " | ".join(mems)
                    else:
                        response = "I don't have any important memories yet."
                    print(f"JARVIS: {response}\n")
                    speak(response)
                    logger.info("assistant=%s", response)
                    continue

                if not is_awake:
                    if is_wake_phrase(text):
                        is_awake = True
                        play_start_sound()
                        speak("I'm awake. How can I help?")
                        launch_orb()
                        last_wake_ts = now
                        print("✓ Woke up and launched orb.")
                        logger.info("event=woke_up")
                    else:
                        print("😴 Sleeping... Say friday, hey friday, or wake up.")
                    continue
                
                if is_wake_phrase(text) and (now - last_wake_ts) >= WAKE_COOLDOWN_SECONDS:
                    play_start_sound()
                    speak("I'm here. How can I help?")
                    launch_orb()
                    last_wake_ts = now
                    print(f"✓ Orb launched. (next trigger in {WAKE_COOLDOWN_SECONDS}s)")
                else:
                    intent = detect_intent(text)
                    if intent == "system_command":
                        response = handle_system_command(text)
                    else:
                        # Normal chat stays fast/stateless-memory unless user explicitly asks memory commands.
                        response = get_llm_response(client, conversation_history, text, memory_context=None)
                    print(f"JARVIS: {response}\n")
                    speak(response)
                    logger.info("assistant=%s", response)
            except Exception as e:
                print(f"Voice error: {e}")
                logger.exception("voice_error")
            finally:
                if wav_file and os.path.exists(wav_file):
                    os.remove(wav_file)
                if denoised_file and os.path.exists(denoised_file):
                    os.remove(denoised_file)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if hotkey_listener:
            try:
                hotkey_listener.stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
