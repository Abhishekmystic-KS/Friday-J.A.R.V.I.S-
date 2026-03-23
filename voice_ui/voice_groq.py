import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import sounddevice as sd
import soundfile as sf
from dotenv import dotenv_values
from groq import Groq

VOICE_UI_DIR = Path(__file__).resolve().parent
ENV_FILE = VOICE_UI_DIR / "env" / ".env"

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 3
MODEL_NAME = "whisper-large-v3-turbo"
WAKE_WORD = "friday"
WAKE_COOLDOWN_SECONDS = 5


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


def transcribe_wav(client: Groq, wav_path: str) -> str:
    with open(wav_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            file=audio_file,
            model=MODEL_NAME,
            language="en",
            temperature=0,
        )
    return (getattr(result, "text", "") or "").strip()


def main() -> None:
    key = load_api_key()
    client = Groq(api_key=key)

    print("Groq voice is active.")
    print(f"Continuous listening started. Say '{WAKE_WORD}' to open the orb.")
    print("Press Ctrl+C to stop.")

    last_wake_ts = 0.0

    try:
        while True:
            wav_file = None
            try:
                wav_file = record_audio_wav()
                text = transcribe_wav(client, wav_file)

                if text:
                    print(f"You said: {text}")
                    now = time.time()
                    if WAKE_WORD in text.lower() and (now - last_wake_ts) >= WAKE_COOLDOWN_SECONDS:
                        play_start_sound()
                        launch_orb()
                        last_wake_ts = now
                        print("Orb launched.")
                else:
                    print("No speech recognized.")
            except Exception as e:
                print(f"Voice error: {e}")
            finally:
                if wav_file and os.path.exists(wav_file):
                    os.remove(wav_file)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
