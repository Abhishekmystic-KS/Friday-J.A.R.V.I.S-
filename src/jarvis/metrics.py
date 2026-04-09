"""Voice UX metrics tracking for diagnostics and optimization."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class VoiceMetrics:
    """Tracks voice interaction quality metrics."""

    def __init__(self, metrics_file: Path | str | None = None):
        self.metrics_file = Path(metrics_file) if metrics_file else None
        self.session_start = time.time()
        self.turn_count = 0
        self.metrics: list[dict[str, Any]] = []

    def log_turn(
        self,
        user_text: str | None = None,
        intent_label: str | None = None,
        intent_confidence: float = 0.0,
        stt_latency_ms: float | None = None,
        llm_latency_ms: float | None = None,
        tts_latency_ms: float | None = None,
        response_length: int = 0,
        tool_used: str | None = None,
        is_clarification: bool = False,
        is_filler_skip: bool = False,
    ) -> None:
        """Log a single turn metric."""
        self.turn_count += 1
        metric = {
            "turn": self.turn_count,
            "timestamp": time.time(),
            "user_text": user_text or "",
            "intent_label": intent_label,
            "intent_confidence": intent_confidence,
            "stt_latency_ms": stt_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "tts_latency_ms": tts_latency_ms,
            "response_length": response_length,
            "tool_used": tool_used,
            "is_clarification": is_clarification,
            "is_filler_skip": is_filler_skip,
        }
        self.metrics.append(metric)

        if self.metrics_file:
            try:
                self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
                with self.metrics_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(metric, ensure_ascii=False) + "\n")
            except Exception:
                pass

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        if not self.metrics:
            return {}

        stt_times = [m["stt_latency_ms"] for m in self.metrics if m["stt_latency_ms"] is not None]
        llm_times = [m["llm_latency_ms"] for m in self.metrics if m["llm_latency_ms"] is not None]
        tts_times = [m["tts_latency_ms"] for m in self.metrics if m["tts_latency_ms"] is not None]
        response_lens = [m["response_length"] for m in self.metrics if m["response_length"] > 0]
        clarifications = sum(1 for m in self.metrics if m["is_clarification"])
        filler_skips = sum(1 for m in self.metrics if m["is_filler_skip"])
        avg_confidence = sum(m["intent_confidence"] for m in self.metrics) / len(self.metrics) if self.metrics else 0

        return {
            "total_turns": len(self.metrics),
            "session_duration_sec": time.time() - self.session_start,
            "avg_intent_confidence": avg_confidence,
            "clarifications_asked": clarifications,
            "filler_skips": filler_skips,
            "stt_avg_ms": sum(stt_times) / len(stt_times) if stt_times else None,
            "llm_avg_ms": sum(llm_times) / len(llm_times) if llm_times else None,
            "tts_avg_ms": sum(tts_times) / len(tts_times) if tts_times else None,
            "avg_response_length": sum(response_lens) / len(response_lens) if response_lens else 0,
        }
