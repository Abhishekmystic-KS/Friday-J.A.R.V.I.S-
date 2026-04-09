from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
import time
from pathlib import Path

import edge_tts
from dotenv import dotenv_values
from groq import Groq

ROOT = Path(__file__).resolve().parents[1]


def load_api_key() -> str:
    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key
    env_file = ROOT / "env" / ".env"
    if env_file.exists():
        file_key = (dotenv_values(env_file).get("GROQ_API_KEY") or "").strip()
        if file_key:
            return file_key
    return ""


async def _edge_save(text: str, voice: str, out_path: str) -> None:
    comm = edge_tts.Communicate(text=text, voice=voice)
    await comm.save(out_path)


def bench_edge(text: str, voice: str) -> tuple[float | None, str | None]:
    audio_path = None
    try:
        t0 = time.perf_counter()
        with tempfile.NamedTemporaryFile(prefix="tts_edge_", suffix=".mp3", delete=False) as tmp:
            audio_path = tmp.name
        asyncio.run(_edge_save(text, voice, audio_path))
        return (time.perf_counter() - t0) * 1000, None
    except Exception as exc:
        return None, str(exc)
    finally:
        if isinstance(audio_path, str) and os.path.exists(audio_path):
            os.remove(audio_path)


def bench_groq(text: str, model: str, voice: str, api_key: str) -> tuple[float | None, str | None]:
    if not api_key:
        return None, "missing GROQ_API_KEY"

    try:
        client = Groq(api_key=api_key)
        t0 = time.perf_counter()
        audio = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="wav",
        )
        _ = audio.read()
        return (time.perf_counter() - t0) * 1000, None
    except Exception as exc:
        return None, str(exc)


def run_benchmark(text: str, edge_voice: str, groq_model: str, groq_voice: str) -> None:
    print("TTS benchmark")
    print("text:", text)
    print("-" * 60)

    edge_ms, edge_err = bench_edge(text, edge_voice)
    if edge_err:
        print("edge: FAIL", edge_err)
    else:
        print(f"edge: OK {edge_ms:.0f}ms")

    api_key = load_api_key()
    groq_ms, groq_err = bench_groq(text, groq_model, groq_voice, api_key)
    if groq_err:
        print("groq: FAIL", groq_err)
    else:
        print(f"groq: OK {groq_ms:.0f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Edge vs Groq TTS latency")
    parser.add_argument("--text", default="System ready. This is a latency check.")
    parser.add_argument("--edge-voice", default="en-US-AriaNeural")
    parser.add_argument("--groq-model", default="canopylabs/orpheus-v1-english")
    parser.add_argument("--groq-voice", default="troy")
    args = parser.parse_args()
    run_benchmark(args.text, args.edge_voice, args.groq_model, args.groq_voice)
