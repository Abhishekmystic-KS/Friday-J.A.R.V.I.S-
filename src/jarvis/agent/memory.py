from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any


class AgentMemory:
    def __init__(self, memory_file: Path | str, short_term_limit: int = 20):
        self.memory_file = Path(memory_file)
        self.short_term_limit = short_term_limit
        self.short_term: list[dict[str, Any]] = []
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def add_short(self, role: str, content: str) -> None:
        self.short_term.append({"role": role, "content": content, "ts": time.time()})
        if len(self.short_term) > self.short_term_limit:
            self.short_term = self.short_term[-self.short_term_limit :]

    def save_long(self, kind: str, content: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        item = {
            "kind": kind,
            "content": content,
            "meta": meta or {},
            "ts": time.time(),
        }
        with self.memory_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    def recall_long(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        if not self.memory_file.exists():
            return []

        q_tokens = set(re.findall(r"\w+", (query or "").lower()))
        if not q_tokens:
            return []

        rows: list[dict[str, Any]] = []
        for line in self.memory_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue

            text = str(item.get("content", ""))
            tokens = set(re.findall(r"\w+", text.lower()))
            overlap = len(q_tokens & tokens)
            if overlap > 0:
                item["_score"] = overlap / max(1, len(q_tokens))
                rows.append(item)

        rows.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return rows[:limit]
