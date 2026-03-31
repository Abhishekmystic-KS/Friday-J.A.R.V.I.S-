import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import edge_tts
import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
from dotenv import dotenv_values
from groq import Groq
from noisereduce import reduce_noise

from jarvis.config import ROOT_DIR, load_config

HOTKEY_SIGNAL = "__HOTKEY_TRIGGERED__"


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def setup_logger(log_file):
    log_path = ROOT_DIR / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("jarvis")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    return logger


def load_api_key():
    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    env_file = ROOT_DIR / "env" / ".env"
    if env_file.exists():
        file_key = (dotenv_values(env_file).get("GROQ_API_KEY") or "").strip()
        if file_key:
            return file_key

    raise RuntimeError("Missing GROQ_API_KEY in env/.env")


def start_hotkey(enabled, combo, event_obj):
    if not enabled:
        return None
    try:
        from pynput import keyboard

        def trigger_hotkey():
            event_obj.set()
            print("[hotkey] pressed")

        listener = keyboard.GlobalHotKeys({combo: trigger_hotkey})
        listener.start()
        print("Hotkey enabled:", combo)
        return listener
    except Exception as exc:
        print("Hotkey disabled:", exc)
        return None


def play_mp3(path):
    player_commands = [
        ["mpg123", "-q", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
        ["paplay", str(path)],
    ]
    for cmd in player_commands:
        if not shutil.which(cmd[0]):
            continue
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            continue
    return False


def play_start_sound():
    start_sound = ROOT_DIR / "assets" / "starting_voice.mp3"
    if start_sound.exists():
        play_mp3(start_sound)


def speak(text, tts_voice):
    if not text:
        return

    print("[tts]", text)
    with tempfile.NamedTemporaryFile(prefix="jarvis_tts_", suffix=".mp3", delete=False) as tmp:
        audio_path = tmp.name

    async def build_audio():
        comm = edge_tts.Communicate(text=text, voice=tts_voice)
        await comm.save(audio_path)

    try:
        asyncio.run(build_audio())
        play_mp3(audio_path)
    except Exception as exc:
        print("TTS error:", exc)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def launch_orb():
    orb_runner = ROOT_DIR / "scripts" / "run_orb.py"
    subprocess.Popen([sys.executable, str(orb_runner)])


def record_with_vad(sample_rate, channels, hotkey_event):
    vad = webrtcvad.Vad(3)
    block_size = int(sample_rate * 0.02)
    frames = []
    silent_blocks = 0

    print("[mic] listening")
    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            blocksize=block_size,
            dtype="float32",
        ) as stream:
            while True:
                if hotkey_event is not None and hotkey_event.is_set():
                    hotkey_event.clear()
                    return HOTKEY_SIGNAL

                chunk, _overflow = stream.read(block_size)
                pcm16 = (chunk * 32767).astype("int16")
                is_speech = vad.is_speech(pcm16.tobytes(), sample_rate)

                if is_speech:
                    frames.append(chunk)
                    silent_blocks = 0
                    continue

                if frames:
                    frames.append(chunk)
                    silent_blocks += 1
                    if silent_blocks > 15:
                        break
    except Exception as exc:
        print("record error:", exc)
        return None

    if not frames:
        return None

    audio_data = np.vstack(frames)
    with tempfile.NamedTemporaryFile(prefix="jarvis_vad_", suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, audio_data, sample_rate)
        return tmp.name


def denoise_wav(path):
    try:
        audio, sample_rate = sf.read(path)
        clean = reduce_noise(y=audio, sr=sample_rate)
        with tempfile.NamedTemporaryFile(prefix="jarvis_dn_", suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, clean, sample_rate)
            return tmp.name
    except Exception:
        return path


def transcribe(client, wav_path, stt_model):
    with open(wav_path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=f,
            model=stt_model,
            language="en",
            temperature=0,
        )
    return (getattr(result, "text", "") or "").strip()


def get_llm_response(client, llm_model, history, user_text, max_history):
    history.append({"role": "user", "content": user_text})
    try:
        result = client.chat.completions.create(
            messages=history,
            model=llm_model,
            max_tokens=120,
            temperature=0.7,
        )
        reply = (result.choices[0].message.content or "").strip()
    except Exception as exc:
        print("LLM error:", exc)
        reply = "Sorry, I could not process that."

    history.append({"role": "assistant", "content": reply})
    if len(history) > max_history + 1:
        history[:] = history[:1] + history[-max_history:]
    return reply


def run_assistant():
    config = load_config()
    logger = setup_logger(config["log_file"])

    sample_rate = int(config["sample_rate"])
    channels = int(config["channels"])
    stt_model = str(config["stt_model"])
    llm_model = str(config["llm_model"])
    wake_phrases = [str(item).lower() for item in config["wake_phrases"]]
    sleep_phrases = [str(item).lower() for item in config["sleep_phrases"]]
    wake_cooldown = int(config["wake_cooldown_seconds"])
    max_history = int(config["max_history_messages"])
    tts_voice = str(config["tts_voice"])

    api_key = load_api_key()
    client = Groq(api_key=api_key)

    hotkey_event = threading.Event()
    hotkey_listener = start_hotkey(
        bool(config.get("hotkey_enabled", False)),
        str(config.get("hotkey_combo", "<ctrl>+<alt>+j")),
        hotkey_event,
    )

    print("Assistant started")
    print("Wake words:", ", ".join(wake_phrases))
    print("Sleep phrases:", ", ".join(sleep_phrases))

    history = [{"role": "system", "content": str(config["system_prompt"])}]
    is_awake = True
    last_wake = 0.0

    try:
        while True:
            wav_path = None
            clean_path = None
            try:
                wav_path = record_with_vad(sample_rate, channels, hotkey_event)
                if wav_path == HOTKEY_SIGNAL:
                    is_awake = True
                    play_start_sound()
                    launch_orb()
                    speak("Hotkey received. I am ready.", tts_voice)
                    continue

                if not wav_path:
                    continue

                clean_path = denoise_wav(wav_path)
                text = transcribe(client, clean_path, stt_model)
                if not text:
                    continue

                print("You said:", text)
                logger.info("user=%s", text)
                now = time.time()
                normalized = normalize_text(text)

                if contains_any(normalized, sleep_phrases):
                    is_awake = False
                    sleep_msg = "Going to sleep. Say friday or hey friday to wake me."
                    speak(sleep_msg, tts_voice)
                    logger.info("assistant=%s", sleep_msg)
                    continue

                if not is_awake:
                    if contains_any(normalized, wake_phrases):
                        is_awake = True
                        play_start_sound()
                        launch_orb()
                        speak("I am awake. How can I help?", tts_voice)
                        last_wake = now
                    continue

                if contains_any(normalized, wake_phrases):
                    if now - last_wake >= wake_cooldown:
                        play_start_sound()
                        launch_orb()
                        speak("I am here. How can I help?", tts_voice)
                        last_wake = now
                    continue

                response = get_llm_response(
                    client,
                    llm_model,
                    history,
                    text,
                    max_history,
                )
                print("JARVIS:", response)
                logger.info("assistant=%s", response)
                speak(response, tts_voice)
            except Exception as exc:
                print("Voice error:", exc)
                logger.exception("voice_error")
            finally:
                if isinstance(wav_path, str) and os.path.exists(wav_path):
                    os.remove(wav_path)
                if isinstance(clean_path, str) and os.path.exists(clean_path):
                    os.remove(clean_path)
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        if hotkey_listener is not None:
            try:
                hotkey_listener.stop()
            except Exception:
                pass


def main():
    run_assistant()


if __name__ == "__main__":
    main()
