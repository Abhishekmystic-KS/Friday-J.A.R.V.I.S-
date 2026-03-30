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
import uuid

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
    return any(p in text for p in phrases)


def setup_logger(log_file):
    path = ROOT_DIR / log_file
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("jarvis")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
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


def play_mp3(path):
    players = [
        ["mpg123", "-q", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
        ["paplay", str(path)],
    ]
    for cmd in players:
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                continue
    return False


def play_start_sound():
    sound = ROOT_DIR / "assets" / "starting_voice.mp3"
    if sound.exists():
        play_mp3(sound)


def speak(text, tts_voice):
    if not text:
        return
    print("[tts]", text)
    with tempfile.NamedTemporaryFile(prefix="jarvis_tts_", suffix=".mp3", delete=False) as tmp:
        audio_path = tmp.name

    async def make_audio():
        comm = edge_tts.Communicate(text=text, voice=tts_voice)
        await comm.save(audio_path)

    try:
        asyncio.run(make_audio())
        play_mp3(audio_path)
    except Exception as exc:
        print("TTS error:", exc)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def launch_orb():
    script = ROOT_DIR / "jarvis_orb_popup.py"
    subprocess.Popen([sys.executable, str(script)])


def record_with_vad(sample_rate, channels, hotkey_event=None):
    vad = webrtcvad.Vad(3)
    block = int(sample_rate * 0.02)
    frames = []
    silent = 0

    print("[mic] listening")
    try:
        with sd.InputStream(samplerate=sample_rate, channels=channels, blocksize=block, dtype="float32") as stream:
            while True:
                if hotkey_event is not None and hotkey_event.is_set():
                    hotkey_event.clear()
                    return HOTKEY_SIGNAL

                chunk, _ = stream.read(block)
                pcm = (chunk * 32767).astype("int16")
                is_speech = vad.is_speech(pcm.tobytes(), sample_rate)

                if is_speech:
                    frames.append(chunk)
                    silent = 0
                elif frames:
                    frames.append(chunk)
                    silent += 1
                    if silent > 15:
                        break
    except Exception as exc:
        print("record error:", exc)
        return None

    if not frames:
        return None

    data = np.vstack(frames)
    with tempfile.NamedTemporaryFile(prefix="jarvis_vad_", suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, data, sample_rate)
        return tmp.name


def denoise_wav(path):
    try:
        audio, sr = sf.read(path)
        clean = reduce_noise(y=audio, sr=sr)
        with tempfile.NamedTemporaryFile(prefix="jarvis_dn_", suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, clean, sr)
            return tmp.name
    except Exception:
        return path


def transcribe(client, wav_path, stt_model):
    with open(wav_path, "rb") as f:
        out = client.audio.transcriptions.create(file=f, model=stt_model, language="en", temperature=0)
    return (getattr(out, "text", "") or "").strip()


def get_llm_response(client, llm_model, history, user_text, max_history):
    history.append({"role": "user", "content": user_text})
    try:
        out = client.chat.completions.create(messages=history, model=llm_model, max_tokens=120, temperature=0.7)
        reply = (out.choices[0].message.content or "").strip()
    except Exception as exc:
        print("LLM error:", exc)
        reply = "Sorry, I could not process that."

    history.append({"role": "assistant", "content": reply})
    if len(history) > max_history + 1:
        del history[1: len(history) - max_history]
    return reply


def run_assistant():
    cfg = load_config()
    logger = setup_logger(cfg["log_file"])

    sample_rate = int(cfg["sample_rate"])
    channels = int(cfg["channels"])
    stt_model = str(cfg["stt_model"])
    llm_model = str(cfg["llm_model"])
    wake_phrases = [str(x).lower() for x in cfg["wake_phrases"]]
    sleep_phrases = [str(x).lower() for x in cfg["sleep_phrases"]]
    wake_cooldown = int(cfg["wake_cooldown_seconds"])
    max_history = int(cfg["max_history_messages"])
    tts_voice = str(cfg["tts_voice"])

    key = load_api_key()
    client = Groq(api_key=key)

    hotkey_event = threading.Event()
    hotkey_listener = start_hotkey(bool(cfg.get("hotkey_enabled", False)), str(cfg.get("hotkey_combo", "<ctrl>+<alt>+j")), hotkey_event)

    print("Assistant started")
    print("Wake words:", ", ".join(wake_phrases))
    print("Sleep phrases:", ", ".join(sleep_phrases))

    history = [{"role": "system", "content": str(cfg["system_prompt"])}]
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
                t = normalize_text(text)

                if contains_any(t, sleep_phrases):
                    is_awake = False
                    msg = "Going to sleep. Say friday or hey friday to wake me."
                    speak(msg, tts_voice)
                    logger.info("assistant=%s", msg)
                    continue

                if not is_awake:
                    if contains_any(t, wake_phrases):
                        is_awake = True
                        play_start_sound()
                        launch_orb()
                        speak("I am awake. How can I help?", tts_voice)
                        last_wake = now
                    continue

                if contains_any(t, wake_phrases) and (now - last_wake) >= wake_cooldown:
                    play_start_sound()
                    launch_orb()
                    speak("I am here. How can I help?", tts_voice)
                    last_wake = now
                    continue

                response = get_llm_response(client, llm_model, history, text, max_history)
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
        if hotkey_listener:
            try:
                hotkey_listener.stop()
            except Exception:
                pass


def main():
    run_assistant()


if __name__ == "__main__":
    run_assistant()
