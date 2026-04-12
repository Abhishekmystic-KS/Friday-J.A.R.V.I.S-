from __future__ import annotations

import json
import re
from typing import Any


def _extract_expr(text: str) -> str | None:
    m = re.search(r"([0-9\s\+\-\*\/\(\)\.\%\^]{3,})", text)
    if not m:
        return None
    return m.group(1).strip()


def _extract_search_query(text: str) -> str | None:
    t = (text or "").strip()
    patterns = [
        r"(?:search for|search)\s+(.+)$",
        r"(?:look up)\s+(.+)$",
        r"(?:google)\s+(.+)$",
        r"(?:find)\s+(.+)$",
    ]
    for p in patterns:
        m = re.search(p, t, flags=re.IGNORECASE)
        if m:
            q = (m.group(1) or "").strip(" .,!?")
            q = re.sub(r"^(?:for\s+)?(?:the\s+)?", "", q, flags=re.IGNORECASE).strip()
            if q:
                return q
    return None


def _intent_label(intent: str | dict[str, Any]) -> str:
    if isinstance(intent, dict):
        return str(intent.get("label", "GENERAL_CHAT"))
    return str(intent or "GENERAL_CHAT")


def heuristic_plan(user_text: str, intent: str | dict[str, Any]) -> list[dict[str, Any]]:
    t = (user_text or "").strip().lower()
    intent_label = _intent_label(intent)

    if intent_label == "SYSTEM_COMMAND":
        app = ""
        for name in ["spotify", "chrome", "firefox", "terminal", "files"]:
            if name in t:
                app = name
                break
        search_query = _extract_search_query(user_text)
        if "open" in t and app:
            params = {"app": app}
            if app in {"chrome", "firefox"} and search_query:
                params["query"] = search_query
                return [
                    {"action": "tool", "tool": "open_app", "params": params, "final": False},
                    {"action": "tool", "tool": "web_search", "params": {"query": search_query, "lines": 2}, "final": False},
                    {
                        "action": "llm",
                        "prompt": "Use ONLY tool observations. Do not invent counts, facts, salaries, or listings. If details are missing, say so briefly.",
                        "final": True,
                    },
                ]
            return [{"action": "tool", "tool": "open_app", "params": params, "final": True}]

    if intent_label == "WEB_SEARCH":
        query = _extract_search_query(user_text) or user_text
        return [
            {"action": "tool", "tool": "open_app", "params": {"app": "firefox", "query": query}, "final": False},
            {"action": "tool", "tool": "web_search", "params": {"query": query, "lines": 2}, "final": False},
            {
                "action": "llm",
                "prompt": "Use ONLY tool observations. Do not invent counts, facts, salaries, or listings. If details are missing, say so briefly.",
                "final": True,
            },
        ]

    if intent_label == "MEMORY_RECALL":
        return [{"action": "tool", "tool": "memory_recall", "params": {"query": user_text}, "final": True}]

    if intent_label == "TASK_MANAGEMENT" and ("remember" in t or "save" in t):
        return [{"action": "tool", "tool": "memory_save", "params": {"content": user_text}, "final": True}]

    expr = _extract_expr(user_text)
    if expr and any(op in expr for op in ["+", "-", "*", "/", "%"]):
        return [{"action": "tool", "tool": "calculator", "params": {"expression": expr}, "final": True}]

    if "time" in t or "date" in t:
        return [{"action": "tool", "tool": "get_time", "params": {}, "final": True}]

    return [{"action": "llm", "prompt": user_text, "final": True}]


def llm_plan(client: Any, model: str, user_text: str, intent: str | dict[str, Any]) -> list[dict[str, Any]] | None:
    if client is None:
        return None

    intent_label = _intent_label(intent)

    prompt = (
        "You are an agent planner. Return strict JSON only: {\"steps\": [...]} with max 3 steps.\n"
        "Allowed actions: tool, llm.\n"
        "Allowed tools: get_time, calculator, open_app, web_search, memory_save, memory_recall.\n"
        "Each step may include: action, tool, params, prompt, final.\n"
        f"Intent: {intent_label}\n"
        f"User text: {user_text}"
    )

    try:
        out = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=220,
        )
        raw = (out.choices[0].message.content or "").strip()
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        payload = json.loads(m.group(0) if m else raw)
        steps = payload.get("steps")
        if not isinstance(steps, list) or not steps:
            return None
        return steps[:3]
    except Exception:
        return None


def make_plan(
    user_text: str,
    intent: str | dict[str, Any],
    *,
    client: Any = None,
    model: str = "llama-3.1-8b-instant",
    use_llm_planner: bool = True,
) -> list[dict[str, Any]]:
    if use_llm_planner:
        plan = llm_plan(client, model, user_text, intent)
        if plan:
            return plan
    return heuristic_plan(user_text, intent)
