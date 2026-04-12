from __future__ import annotations

import ast
import datetime as dt
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus

import requests

try:
    from scrapling.fetchers import Fetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False

from .memory import AgentMemory


def _compact_lines(lines: list[str], max_lines: int = 2, max_len: int = 180) -> str:
    compact: list[str] = []
    for line in lines:
        cleaned = " ".join(str(line).split())
        if len(cleaned) > max_len:
            cleaned = cleaned[: max_len - 3].rstrip() + "..."
        compact.append(cleaned)
    return "\n".join(compact[:max_lines])


def _news_headlines_fallback(query: str, max_lines: int) -> str | None:
    # RSS fallback for news-style queries when instant summary is empty.
    rss_url = "https://news.google.com/rss/search"
    q = f"{query} when:1d"
    resp = requests.get(
        rss_url,
        params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        timeout=8,
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    items = root.findall("./channel/item")
    headlines: list[str] = []
    for item in items[: max(2, max_lines)]:
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        headlines.append(f"Headline: {title}")

    if not headlines:
        return None

    return _compact_lines(headlines, max_lines=max_lines)


def _safe_eval(expr: str) -> float:
    allowed = {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Num,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.FloorDiv,
        ast.Load,
    }

    node = ast.parse(expr, mode="eval")
    for n in ast.walk(node):
        if type(n) not in allowed:
            raise ValueError("unsafe_expression")

    return float(eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {}))


def _scrapling_web_search(query: str, max_lines: int = 2) -> str | None:
    """
    Use Scrapling with stealthy headers to fetch search results.
    Handles Cloudflare protection and anti-bot detection.
    Falls back to None if Scrapling fails or is unavailable.
    """
    if not SCRAPLING_AVAILABLE:
        return None

    try:
        # Fetch DuckDuckGo search results with Scrapling's stealthy capabilities
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        page = Fetcher.get(search_url, stealthy_headers=True, timeout=8)

        # Try multiple selectors to extract snippets
        snippets = page.css(".result__snippet::text").getall()
        if not snippets:
            snippets = page.css(".result__body::text").getall()
        if not snippets:
            snippets = page.css("a.result__a::text").getall()  # Try titles
        
        # Filter out generic/short results and keep meaningful ones
        meaningful = [s.strip() for s in snippets if s.strip() and len(s.strip()) > 15]
        
        if meaningful:
            lines = [f"- {snippet}" for snippet in meaningful[:3]]
            return _compact_lines(lines, max_lines=max_lines)

        return None
    except Exception as exc:
        # Scrapling failed; will fall back to API-based search
        return None


def tool_get_time(_: dict[str, Any], __: AgentMemory, ___: Path) -> dict[str, Any]:
    now = dt.datetime.now()
    return {"status": "ok", "output": now.strftime("%Y-%m-%d %H:%M:%S")}


def tool_calculator(params: dict[str, Any], __: AgentMemory, ___: Path) -> dict[str, Any]:
    expr = str(params.get("expression", "")).strip()
    if not expr:
        return {"status": "error", "output": "missing expression"}
    try:
        value = _safe_eval(expr)
        return {"status": "ok", "output": str(value)}
    except Exception as exc:
        return {"status": "error", "output": f"calculation failed: {exc}"}


def tool_open_app(params: dict[str, Any], __: AgentMemory, ___: Path) -> dict[str, Any]:
    app = str(params.get("app", "")).strip().lower()
    query = str(params.get("query", "")).strip()
    if not app:
        return {"status": "error", "output": "missing app"}

    app_map = {
        "chrome": ["google-chrome"],
        "firefox": ["firefox"],
        "spotify": ["spotify"],
        "terminal": ["x-terminal-emulator"],
        "files": ["xdg-open", str(Path.home())],
    }

    cmd = app_map.get(app)
    if not cmd:
        return {"status": "error", "output": f"unsupported app: {app}"}

    # If it's a browser and query is present, open web search directly on screen.
    if app in {"chrome", "firefox"} and query:
        search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        cmd = [cmd[0], search_url]

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app in {"chrome", "firefox"} and query:
            return {"status": "ok", "output": f"opened {app} and searched: {query}"}
        return {"status": "ok", "output": f"opened {app}"}
    except Exception as exc:
        return {"status": "error", "output": f"failed to open {app}: {exc}"}


def tool_web_search(params: dict[str, Any], __: AgentMemory, ___: Path) -> dict[str, Any]:
    query = str(params.get("query", "")).strip()
    query = query.strip(" .,!?")
    query = re.sub(r"^(?:for\s+)?(?:the\s+)?", "", query, flags=re.IGNORECASE).strip()
    max_lines = int(params.get("lines", 2))
    max_lines = 2 if max_lines < 1 else min(max_lines, 4)
    if not query:
        return {"status": "error", "output": "missing query"}

    # Detect if query is asking for news
    is_news_query = any(k in query.lower() for k in ["news", "latest", "today", "headline", "update", "recent", "breaking"])
    
    # For news queries, try Google News RSS first (returns actual headlines)
    if is_news_query:
        try:
            news = _news_headlines_fallback(query, max_lines=max_lines)
            if news:
                return {"status": "ok", "output": news, "source": "google_news_rss"}
        except Exception:
            pass
    
    # Try Scrapling for regular searches (stealthy, handles anti-bot)
    try:
        result = _scrapling_web_search(query, max_lines=max_lines)
        if result:
            return {"status": "ok", "output": result, "source": "scrapling"}
    except Exception:
        pass

    # Fall back to DuckDuckGo API
    try:
        url = "https://api.duckduckgo.com/"
        resp = requests.get(
            url,
            params={
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1",
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        abstract = (data.get("AbstractText") or "").strip()
        heading = (data.get("Heading") or "").strip()
        related = data.get("RelatedTopics") or []

        lines: list[str] = []
        if heading:
            lines.append(f"Topic: {heading}")
        if abstract:
            lines.append(f"Summary: {abstract}")

        count = 0
        for item in related:
            if isinstance(item, dict) and item.get("Text"):
                lines.append(f"Key point: {item['Text']}")
                count += 1
            if count >= 3:
                break

        if lines:
            return {"status": "ok", "output": _compact_lines(lines, max_lines=max_lines), "source": "duckduckgo"}

        # Last resort: try news fallback again if not already tried
        if not is_news_query:
            news = _news_headlines_fallback(query, max_lines=max_lines)
            if news:
                return {"status": "ok", "output": news, "source": "google_news_rss_fallback"}

        return {"status": "ok", "output": "no concise web result found", "source": "none"}
    except Exception as exc:
        return {"status": "error", "output": f"web search failed: {exc}"}


def tool_memory_save(params: dict[str, Any], memory: AgentMemory, __: Path) -> dict[str, Any]:
    content = str(params.get("content", "")).strip()
    if not content:
        return {"status": "error", "output": "missing content"}
    memory.save_long("fact", content, meta={"source": "agent_tool"})
    return {"status": "ok", "output": "memory saved"}


def tool_memory_recall(params: dict[str, Any], memory: AgentMemory, __: Path) -> dict[str, Any]:
    query = str(params.get("query", "")).strip()
    if not query:
        return {"status": "error", "output": "missing query"}
    items = memory.recall_long(query, limit=int(params.get("limit", 3)))
    if not items:
        return {"status": "ok", "output": "no memory matches"}
    lines = [f"- {x.get('content', '')}" for x in items]
    return {"status": "ok", "output": "\n".join(lines)}


def build_tool_registry(memory: AgentMemory, root_dir: Path) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    def bind(fn):
        return lambda params=None: fn(params or {}, memory, root_dir)

    return {
        "get_time": bind(tool_get_time),
        "calculator": bind(tool_calculator),
        "open_app": bind(tool_open_app),
        "web_search": bind(tool_web_search),
        "memory_save": bind(tool_memory_save),
        "memory_recall": bind(tool_memory_recall),
    }
