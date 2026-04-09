from __future__ import annotations

import json
import re
from typing import Any

INTENT_LABELS = {
    "SYSTEM_COMMAND",
    "KNOWLEDGE_QUERY",
    "DOCUMENT_TASK",
    "TASK_MANAGEMENT",
    "WEB_SEARCH",
    "MEMORY_RECALL",
    "GENERAL_CHAT",
}


def _keyword_intent(text: str) -> dict[str, Any]:
    t = (text or "").strip().lower()

    if any(k in t for k in ["open ", "launch ", "start ", "close ", "shutdown", "restart"]):
        return {"label": "SYSTEM_COMMAND", "confidence": 0.72, "method": "keyword"}

    if any(k in t for k in ["search", "latest", "news", "on the web", "google", "browse"]):
        return {"label": "WEB_SEARCH", "confidence": 0.7, "method": "keyword"}

    if any(k in t for k in ["what did i", "last time", "my preference", "recall", "do you remember", "remember what"]):
        return {"label": "MEMORY_RECALL", "confidence": 0.7, "method": "keyword"}

    if any(k in t for k in ["pdf", "document", "file", "summarize this", "extract"]):
        return {"label": "DOCUMENT_TASK", "confidence": 0.68, "method": "keyword"}

    if any(k in t for k in ["remember that", "save this", "note that", "remind", "schedule", "todo", "task"]):
        return {"label": "TASK_MANAGEMENT", "confidence": 0.66, "method": "keyword"}

    # Time-like task scheduling hint such as "at 5" or "at 5 pm"
    if re.search(r"\bat\s+\d{1,2}(?::\d{2})?\b", t):
        return {"label": "TASK_MANAGEMENT", "confidence": 0.66, "method": "keyword"}

    if any(k in t for k in ["what", "who", "why", "how", "when", "explain", "tell me"]):
        return {"label": "KNOWLEDGE_QUERY", "confidence": 0.62, "method": "keyword"}

    return {"label": "GENERAL_CHAT", "confidence": 0.55, "method": "keyword"}


def _llm_intent(client: Any, model: str, text: str) -> dict[str, Any] | None:
    if client is None:
        return None

    prompt = (
        "Classify the user intent into exactly one label from this set: "
        "SYSTEM_COMMAND, KNOWLEDGE_QUERY, DOCUMENT_TASK, TASK_MANAGEMENT, WEB_SEARCH, MEMORY_RECALL, GENERAL_CHAT. "
        "Return strict JSON only with keys: label, confidence. "
        "Confidence must be a number between 0 and 1.\n\n"
        f"User text: {text}"
    )

    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an intent classifier. Output JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=80,
        )
        raw = (result.choices[0].message.content or "").strip()

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        payload = json.loads(match.group(0) if match else raw)
        label = str(payload.get("label", "")).strip().upper()
        confidence = float(payload.get("confidence", 0.0))

        if label not in INTENT_LABELS:
            return None

        confidence = max(0.0, min(1.0, confidence))
        return {"label": label, "confidence": confidence, "method": "llm"}
    except Exception:
        return None


def classify_intent(
    text: str,
    *,
    mode: str = "hybrid",
    client: Any = None,
    model: str = "llama-3.1-8b-instant",
) -> dict[str, Any]:
    """Phase-1 intent classifier with keyword + optional LLM fallback.

    Returns: {label, confidence, method}
    """
    mode = (mode or "hybrid").strip().lower()

    if mode == "keyword":
        return _keyword_intent(text)

    if mode == "llm":
        llm_out = _llm_intent(client, model, text)
        return llm_out or _keyword_intent(text)

    # hybrid
    llm_out = _llm_intent(client, model, text)
    if llm_out and llm_out.get("confidence", 0) >= 0.6:
        return llm_out
    return _keyword_intent(text)
