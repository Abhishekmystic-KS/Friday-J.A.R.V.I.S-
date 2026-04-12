import asyncio
import logging
import os
import queue
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

from jarvis.agent import AgentMemory, build_tool_registry, classify_intent, run_agent_task
from jarvis.config import ROOT_DIR, load_config
from jarvis.metrics import VoiceMetrics

HOTKEY_SIGNAL = "__HOTKEY_TRIGGERED__"


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_filler_speech(text, filler_patterns):
    """Check if text is mostly filler/noise and should be skipped."""
    normalized = normalize_text(text)
    if not normalized:
        return False
    
    # Single word that matches a filler pattern
    words = normalized.split()
    if len(words) <= 1 and words[0] in filler_patterns:
        return True
    
    # All words are fillers (e.g., "uh um okay")
    if all(w in filler_patterns for w in words):
        return True
    
    return False


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


def synthesize_edge_tts_to_mp3(text, tts_voice):
    with tempfile.NamedTemporaryFile(prefix="jarvis_tts_", suffix=".mp3", delete=False) as tmp:
        audio_path = tmp.name

    async def build_audio():
        comm = edge_tts.Communicate(text=text, voice=tts_voice)
        await comm.save(audio_path)

    asyncio.run(build_audio())
    return audio_path


def split_text_for_tts(text, max_chars=200):
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    parts = re.split(r"(?<=[.!?])\s+", text)
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if len(part) > max_chars:
            words = part.split()
            sub = ""
            for word in words:
                next_sub = f"{sub} {word}".strip()
                if len(next_sub) > max_chars and sub:
                    chunks.append(sub)
                    sub = word
                else:
                    sub = next_sub
            if sub:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(sub)
            continue

        candidate = f"{current} {part}".strip() if current else part
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = part
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks


def synthesize_groq_tts_to_wav(text, groq_client, groq_model, groq_voice):
    response = groq_client.audio.speech.create(
        model=groq_model,
        voice=groq_voice,
        input=text,
        response_format="wav",
    )
    data = response.read()
    with tempfile.NamedTemporaryFile(prefix="jarvis_groq_tts_", suffix=".wav", delete=False) as tmp:
        tmp.write(data)
        return tmp.name


def benchmark_tts_provider(
    provider,
    sample_text,
    tts_voice,
    *,
    groq_client=None,
    groq_tts_model="canopylabs/orpheus-v1-english",
    groq_tts_voice="troy",
):
    t0 = time.perf_counter()
    if provider == "edge":
        audio_path = None
        try:
            audio_path = synthesize_edge_tts_to_mp3(sample_text, tts_voice)
            return (time.perf_counter() - t0) * 1000
        except Exception:
            return None
        finally:
            if isinstance(audio_path, str) and os.path.exists(audio_path):
                os.remove(audio_path)

    if provider == "espeak":
        if not shutil.which("espeak"):
            return None
        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="jarvis_espeak_", suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            subprocess.run(
                ["espeak", "-w", wav_path, sample_text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return (time.perf_counter() - t0) * 1000
        except Exception:
            return None
        finally:
            if isinstance(wav_path, str) and os.path.exists(wav_path):
                os.remove(wav_path)

    if provider == "groq":
        if groq_client is None:
            return None
        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="jarvis_groq_bench_", suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            response = groq_client.audio.speech.create(
                model=groq_tts_model,
                voice=groq_tts_voice,
                input=sample_text[:200],
                response_format="wav",
            )
            data = response.read()
            with open(wav_path, "wb") as f:
                f.write(data)
            return (time.perf_counter() - t0) * 1000
        except Exception:
            return None
        finally:
            if isinstance(wav_path, str) and os.path.exists(wav_path):
                os.remove(wav_path)

    return None


def select_tts_provider(
    tts_provider,
    tts_voice,
    benchmark_text,
    logger,
    verbose=False,
    *,
    groq_enabled=False,
    groq_client=None,
    groq_tts_model="canopylabs/orpheus-v1-english",
    groq_tts_voice="troy",
):
    preferred = (tts_provider or "edge").strip().lower()
    if preferred in {"edge", "espeak", "groq"}:
        if preferred == "groq" and not groq_enabled:
            print("[tts] groq disabled in config, falling back to edge")
            logger.info("tts_provider_fallback=groq_disabled")
            return "edge"
        if preferred == "espeak" and not shutil.which("espeak"):
            print("[tts] espeak not found, falling back to edge")
            logger.info("tts_provider_fallback=espeak_missing")
            return "edge"
        return preferred

    if preferred != "auto":
        return "edge"

    candidates = ["edge", "espeak"]
    if groq_enabled:
        candidates.append("groq")
    timings = {}
    for provider in candidates:
        ms = benchmark_tts_provider(
            provider,
            benchmark_text,
            tts_voice,
            groq_client=groq_client,
            groq_tts_model=groq_tts_model,
            groq_tts_voice=groq_tts_voice,
        )
        if ms is not None:
            timings[provider] = ms

    if not timings:
        return "edge"

    chosen = min(timings, key=timings.get)
    timing_text = ", ".join(f"{name}={value:.0f}ms" for name, value in timings.items())
    if verbose:
        print(f"[tts] auto selected {chosen} ({timing_text})")
        logger.info("tts_auto_selected=%s timings=%s", chosen, timing_text)
    return chosen


def speak(
    text,
    tts_voice,
    tts_provider,
    logger,
    latency_logging_enabled,
    *,
    groq_client=None,
    groq_tts_model="canopylabs/orpheus-v1-english",
    groq_tts_voice="troy",
):
    if not text:
        return

    if latency_logging_enabled:
        print(f"[tts/{tts_provider}]", text)
    t0 = time.perf_counter()
    synth_ms = 0.0
    play_ms = 0.0
    played = False

    try:
        if tts_provider == "espeak":
            t_play = time.perf_counter()
            subprocess.run(
                ["espeak", "-s", "170", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            play_ms = (time.perf_counter() - t_play) * 1000
            played = True
        elif tts_provider == "groq":
            client = groq_client
            if client is None:
                client = Groq(api_key=load_api_key())

            for chunk in split_text_for_tts(text, max_chars=200):
                audio_path = None
                try:
                    t_synth = time.perf_counter()
                    audio_path = synthesize_groq_tts_to_wav(chunk, client, groq_tts_model, groq_tts_voice)
                    synth_ms += (time.perf_counter() - t_synth) * 1000

                    t_play = time.perf_counter()
                    chunk_played = play_mp3(audio_path)
                    play_ms += (time.perf_counter() - t_play) * 1000
                    played = played or chunk_played
                finally:
                    if isinstance(audio_path, str) and os.path.exists(audio_path):
                        os.remove(audio_path)
        else:
            audio_path = None
            try:
                t_synth = time.perf_counter()
                audio_path = synthesize_edge_tts_to_mp3(text, tts_voice)
                synth_ms = (time.perf_counter() - t_synth) * 1000

                t_play = time.perf_counter()
                played = play_mp3(audio_path)
                play_ms = (time.perf_counter() - t_play) * 1000
            finally:
                if isinstance(audio_path, str) and os.path.exists(audio_path):
                    os.remove(audio_path)
    except Exception as exc:
        print("TTS error:", exc)
        # If Groq fails at runtime (terms/network/etc), auto-fallback to edge.
        if tts_provider == "groq":
            try:
                audio_path = synthesize_edge_tts_to_mp3(text, tts_voice)
                played = play_mp3(audio_path)
            except Exception:
                pass
            finally:
                if "audio_path" in locals() and isinstance(audio_path, str) and os.path.exists(audio_path):
                    os.remove(audio_path)

    total_ms = (time.perf_counter() - t0) * 1000
    if latency_logging_enabled:
        msg = (
            f"[latency] tts provider={tts_provider} total={total_ms:.0f}ms "
            f"synth={synth_ms:.0f}ms play={play_ms:.0f}ms played={played}"
        )
        print(msg)
        logger.info(msg)


def is_process_running(proc):
    return proc is not None and proc.poll() is None


def stop_process(proc):
    if not is_process_running(proc):
        return None

    try:
        proc.terminate()
        proc.wait(timeout=1.5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    return None


def launch_orb(current_proc=None):
    if is_process_running(current_proc):
        return current_proc

    orb_runner = ROOT_DIR / "scripts" / "run_orb.py"
    try:
        return subprocess.Popen(
            [sys.executable, str(orb_runner)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        return None


def launch_robo_popup(current_proc=None):
    if is_process_running(current_proc):
        return current_proc

    robo_runner = ROOT_DIR / "scripts" / "run_robo.py"
    if not robo_runner.exists():
        return None
    try:
        return subprocess.Popen(
            [sys.executable, str(robo_runner)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        return None


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


def pop_complete_sentences(buffer):
    sentences = []
    while True:
        match = re.search(r"[.!?](?:\s+|$)", buffer)
        if not match:
            break

        end = match.end()
        sentence = buffer[:end].strip()
        buffer = buffer[end:].lstrip()
        if sentence:
            sentences.append(sentence)

    return sentences, buffer


def append_history_turn(history, user_text, assistant_text, max_history):
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": assistant_text})
    if len(history) > max_history + 1:
        history[:] = history[:1] + history[-max_history:]


def stream_llm_response_and_speak(
    client,
    llm_model,
    history,
    user_text,
    max_history,
    tts_voice,
    tts_provider,
    logger,
    latency_logging_enabled,
    groq_tts_client=None,
    groq_tts_model="canopylabs/orpheus-v1-english",
    groq_tts_voice="troy",
):
    history.append({"role": "user", "content": user_text})

    stop_token = object()
    tts_queue = queue.Queue()

    def tts_worker():
        while True:
            item = tts_queue.get()
            try:
                if item is stop_token:
                    return
                speak(
                    item,
                    tts_voice,
                    tts_provider,
                    logger,
                    latency_logging_enabled,
                    groq_client=groq_tts_client,
                    groq_tts_model=groq_tts_model,
                    groq_tts_voice=groq_tts_voice,
                )
            finally:
                tts_queue.task_done()

    worker = threading.Thread(target=tts_worker, daemon=True)
    worker.start()

    reply = ""
    buffer = ""
    t0 = time.perf_counter()

    try:
        stream = client.chat.completions.create(
            model=llm_model,
            messages=history,
            max_tokens=120,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = ""
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = ""

            if not delta:
                continue

            reply += delta
            buffer += delta

            sentences, buffer = pop_complete_sentences(buffer)
            for sentence in sentences:
                tts_queue.put(sentence)

        tail = buffer.strip()
        if tail:
            tts_queue.put(tail)
    except Exception as exc:
        print("LLM error:", exc)
        logger.exception("llm_stream_error")
        if not reply:
            reply = "Sorry, I could not process that."
            tts_queue.put(reply)

    tts_queue.put(stop_token)
    tts_queue.join()
    worker.join(timeout=1.0)

    reply = reply.strip() or "Sorry, I could not process that."
    history.append({"role": "assistant", "content": reply})
    if len(history) > max_history + 1:
        history[:] = history[:1] + history[-max_history:]

    if latency_logging_enabled:
        llm_stream_ms = (time.perf_counter() - t0) * 1000
        msg = f"[latency] llm_stream_total={llm_stream_ms:.0f}ms"
        print(msg)
        logger.info(msg)

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
    tts_groq_enabled = bool(config.get("tts_groq_enabled", False))
    tts_groq_model = str(config.get("tts_groq_model", "canopylabs/orpheus-v1-english"))
    tts_groq_voice = str(config.get("tts_groq_voice", "troy"))
    tts_benchmark_text = str(config.get("tts_benchmark_text", "System ready. This is a latency check."))
    denoise_enabled = bool(config.get("denoise_enabled", False))
    latency_logging_enabled = bool(config.get("latency_logging_enabled", True))
    agent_enabled = bool(config.get("agent_enabled", False))
    agent_phase = int(config.get("agent_phase", 1))
    intent_mode = str(config.get("intent_classifier_mode", "hybrid"))
    intent_model = str(config.get("intent_classifier_model", llm_model))
    intent_logging_enabled = bool(config.get("intent_logging_enabled", True))
    agent_max_steps = int(config.get("agent_max_steps", 4))
    agent_replan_enabled = bool(config.get("agent_replan_enabled", True))
    agent_use_llm_planner = bool(config.get("agent_use_llm_planner", True))
    agent_memory_enabled = bool(config.get("agent_memory_enabled", True))
    agent_memory_file = ROOT_DIR / str(config.get("agent_memory_file", "data/memory/agent_memory.jsonl"))

    api_key = load_api_key()
    client = Groq(api_key=api_key)

    tts_provider = select_tts_provider(
        str(config.get("tts_provider", "auto")),
        tts_voice,
        tts_benchmark_text,
        logger,
        latency_logging_enabled,
        groq_enabled=tts_groq_enabled,
        groq_client=client,
        groq_tts_model=tts_groq_model,
        groq_tts_voice=tts_groq_voice,
    )

    groq_tts_client = client if tts_groq_enabled else None
    if tts_provider == "groq":
        groq_probe = benchmark_tts_provider(
            "groq",
            tts_benchmark_text,
            tts_voice,
            groq_client=client,
            groq_tts_model=tts_groq_model,
            groq_tts_voice=tts_groq_voice,
        )
        if groq_probe is None:
            tts_provider = "edge"
            print("[tts] groq unavailable right now, using edge")
            logger.info("tts_provider_fallback=groq_unavailable")

    agent_memory = AgentMemory(agent_memory_file)
    agent_tools = build_tool_registry(agent_memory, ROOT_DIR)

    # Initialize metrics tracking
    metrics_enabled = bool(config.get("voice_ux_metrics_enabled", False))
    metrics_file = ROOT_DIR / "data/logs/voice_metrics.jsonl" if metrics_enabled else None
    voice_metrics = VoiceMetrics(metrics_file)

    hotkey_event = threading.Event()
    hotkey_listener = start_hotkey(
        bool(config.get("hotkey_enabled", False)),
        str(config.get("hotkey_combo", "<ctrl>+<alt>+j")),
        hotkey_event,
    )

    print("Assistant started")
    print("Wake words:", ", ".join(wake_phrases))
    print("Sleep phrases:", ", ".join(sleep_phrases))
    print("Denoise enabled:", denoise_enabled)
    print("TTS provider:", tts_provider)
    if agent_enabled:
        print(f"Agent mode: enabled (phase={agent_phase}, intent={intent_mode})")

    # Start with idle orb visible.
    orb_process = launch_orb()
    robo_process = None

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
                    orb_process = stop_process(orb_process)
                    robo_process = launch_robo_popup(robo_process)
                    if not is_process_running(robo_process):
                        orb_process = launch_orb(orb_process)
                    speak(
                        "Hotkey received. I am ready.",
                        tts_voice,
                        tts_provider,
                        logger,
                        latency_logging_enabled,
                        groq_client=groq_tts_client,
                        groq_tts_model=tts_groq_model,
                        groq_tts_voice=tts_groq_voice,
                    )
                    continue

                if not wav_path:
                    continue

                stt_input_path = wav_path
                if denoise_enabled:
                    t_denoise = time.perf_counter()
                    clean_path = denoise_wav(wav_path)
                    stt_input_path = clean_path
                    if latency_logging_enabled:
                        denoise_ms = (time.perf_counter() - t_denoise) * 1000
                        msg = f"[latency] denoise={denoise_ms:.0f}ms"
                        print(msg)
                        logger.info(msg)

                t_stt = time.perf_counter()
                text = transcribe(client, stt_input_path, stt_model)
                if latency_logging_enabled:
                    stt_ms = (time.perf_counter() - t_stt) * 1000
                    msg = f"[latency] stt={stt_ms:.0f}ms"
                    print(msg)
                    logger.info(msg)
                if not text:
                    continue

                print("You said:", text)
                logger.info("user=%s", text)
                now = time.time()
                normalized = normalize_text(text)

                # Skip filler speech (uh, hmm, yeah, etc.)
                filler_patterns = config.get("voice_ux_filler_patterns", [])
                if is_filler_speech(text, filler_patterns):
                    logger.info("filler_skipped=%s", text)
                    if metrics_enabled:
                        voice_metrics.log_turn(
                            user_text=text,
                            is_filler_skip=True,
                        )
                    continue

                if contains_any(normalized, sleep_phrases):
                    is_awake = False
                    robo_process = stop_process(robo_process)
                    orb_process = launch_orb(orb_process)
                    sleep_msg = "Going to sleep. Say friday or hey friday to wake me."
                    speak(
                        sleep_msg,
                        tts_voice,
                        tts_provider,
                        logger,
                        latency_logging_enabled,
                        groq_client=groq_tts_client,
                        groq_tts_model=tts_groq_model,
                        groq_tts_voice=tts_groq_voice,
                    )
                    logger.info("assistant=%s", sleep_msg)
                    continue

                if not is_awake:
                    if contains_any(normalized, wake_phrases):
                        is_awake = True
                        play_start_sound()
                        orb_process = stop_process(orb_process)
                        robo_process = launch_robo_popup(robo_process)
                        if not is_process_running(robo_process):
                            orb_process = launch_orb(orb_process)
                        speak(
                            "I am awake. How can I help?",
                            tts_voice,
                            tts_provider,
                            logger,
                            latency_logging_enabled,
                            groq_client=groq_tts_client,
                            groq_tts_model=tts_groq_model,
                            groq_tts_voice=tts_groq_voice,
                        )
                        last_wake = now
                    continue

                if contains_any(normalized, wake_phrases):
                    if now - last_wake >= wake_cooldown:
                        play_start_sound()
                        orb_process = stop_process(orb_process)
                        robo_process = launch_robo_popup(robo_process)
                        if not is_process_running(robo_process):
                            orb_process = launch_orb(orb_process)
                        speak(
                            "I am here. How can I help?",
                            tts_voice,
                            tts_provider,
                            logger,
                            latency_logging_enabled,
                            groq_client=groq_tts_client,
                            groq_tts_model=tts_groq_model,
                            groq_tts_voice=tts_groq_voice,
                        )
                        last_wake = now
                    continue

                intent = {"label": "GENERAL_CHAT", "confidence": 0.0, "method": "default"}
                confidence_threshold = float(config.get("voice_ux_confidence_threshold", 0.55))
                clarification_enabled = bool(config.get("voice_ux_clarification_on_low_confidence", True))
                response_max_lines = int(config.get("voice_ux_response_max_lines", 2))
                
                if agent_enabled and agent_phase >= 1:
                    intent = classify_intent(
                        text,
                        mode=intent_mode,
                        client=client,
                        model=intent_model,
                    )
                    if intent_logging_enabled:
                        phase_tag = "p1" if agent_phase == 1 else f"p{agent_phase}"
                        intent_msg = (
                            f"[agent:{phase_tag}] intent={intent.get('label')} "
                            f"confidence={intent.get('confidence', 0):.2f} "
                            f"method={intent.get('method')}"
                        )
                        print(intent_msg)
                        logger.info(intent_msg)

                # Low-confidence clarification: ask user to repeat if confidence too low
                if agent_enabled and agent_phase >= 1 and clarification_enabled:
                    conf = float(intent.get("confidence", 0))
                    if conf < confidence_threshold:
                        clarify_msg = "Sorry, could you say that again?"
                        speak(
                            clarify_msg,
                            tts_voice,
                            tts_provider,
                            logger,
                            latency_logging_enabled,
                            groq_client=groq_tts_client,
                            groq_tts_model=tts_groq_model,
                            groq_tts_voice=tts_groq_voice,
                        )
                        logger.info("clarification=%s confidence=%.2f", clarify_msg, conf)
                        print("JARVIS:", clarify_msg)
                        if metrics_enabled:
                            voice_metrics.log_turn(
                                user_text=text,
                                intent_label=intent.get("label"),
                                intent_confidence=conf,
                                response_length=len(clarify_msg),
                                is_clarification=True,
                            )
                        continue

                if agent_enabled and agent_phase >= 2:
                    agent_result = run_agent_task(
                        text,
                        str(intent.get("label", "GENERAL_CHAT")),
                        client=client,
                        llm_model=llm_model,
                        tools=agent_tools,
                        max_steps=agent_max_steps,
                        replan_enabled=agent_replan_enabled,
                        use_llm_planner=agent_use_llm_planner,
                        logger=logger,
                        response_max_lines=response_max_lines,
                    )
                    response = str(agent_result.get("response", "Sorry, I could not process that."))
                    if agent_memory_enabled:
                        agent_memory.add_short("user", text)
                        agent_memory.add_short("assistant", response)
                        agent_memory.save_long(
                            "task_trace",
                            response,
                            meta={
                                "intent": intent.get("label"),
                                "observations": agent_result.get("observations", []),
                                "plan": agent_result.get("plan", []),
                            },
                        )

                    append_history_turn(history, text, response, max_history)
                    speak(
                        response,
                        tts_voice,
                        tts_provider,
                        logger,
                        latency_logging_enabled,
                        groq_client=groq_tts_client,
                        groq_tts_model=tts_groq_model,
                        groq_tts_voice=tts_groq_voice,
                    )
                    if metrics_enabled:
                        voice_metrics.log_turn(
                            user_text=text,
                            intent_label=intent.get("label"),
                            intent_confidence=intent.get("confidence", 0),
                            response_length=len(response),
                            tool_used=agent_result.get("plan", [{}])[0].get("tool"),
                        )
                else:
                    response = stream_llm_response_and_speak(
                        client,
                        llm_model,
                        history,
                        text,
                        max_history,
                        tts_voice,
                        tts_provider,
                        logger,
                        latency_logging_enabled,
                        groq_tts_client=groq_tts_client,
                        groq_tts_model=tts_groq_model,
                        groq_tts_voice=tts_groq_voice,
                    )

                print("JARVIS:", response)
                logger.info("assistant=%s", response)
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
        stop_process(robo_process)
        stop_process(orb_process)
        if hotkey_listener is not None:
            try:
                hotkey_listener.stop()
            except Exception:
                pass


def main():
    run_assistant()


if __name__ == "__main__":
    main()
