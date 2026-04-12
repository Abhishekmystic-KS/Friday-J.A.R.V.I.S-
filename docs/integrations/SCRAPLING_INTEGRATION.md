# Scrapling Web Search Integration

## Overview

Scrapling has been integrated into J.A.R.V.I.S as the **primary web search backend**, replacing reliance on the DuckDuckGo instant-answer API alone. Scrapling provides stealthy, anti-bot-protected web scraping with fallback to traditional APIs.

## Why Scrapling?

| Feature | Benefit |
|---------|---------|
| **Stealthy Headers** | Bypasses basic bot detection on search result pages |
| **Anti-Cloudflare** | Handles Cloudflare-protected sites seamlessly |
| **Async Capable** | Non-blocking, won't freeze Jarvis during scraping |
| **MCP Built-in** | Optional direct integration with agent brain |
| **Maintained** | 22.7k stars, battle-tested production library |
| **Fast** | Optimized for Python, good for resource-constrained systems |

## Architecture

```
User: "Search latest AI news"
    ↓
Agent Intent Classification (WEB_SEARCH)
    ↓
web_search() tool called
    ↓
1. Try Scrapling.Fetcher (stealthy) → CSS selectors → results?
    ↓ (fallback if empty/error)
2. Try DuckDuckGo API (instant-answer) → parse abstract + related
    ↓ (fallback if empty)
3. Try Google News RSS (news-like queries only) → headlines
    ↓
Return 2-line summary to user → speak via TTS
```

## Configuration

### app.json Flags

```json
{
  "web_search_provider": "auto",           // "auto" | "scrapling" | "duckduckgo"
  "web_search_scrapling_enabled": true,    // Enable/disable Scrapling attempts
  "web_search_timeout": 8                  // Timeout in seconds per fetch
}
```

### Behavior

| Config | Behavior |
|--------|----------|
| `web_search_provider: "auto"` | Try Scrapling first, fall back to APIs if unavailable |
| `web_search_provider: "scrapling"` | Only use Scrapling; error if unavailable |
| `web_search_provider: "duckduckgo"` | Skip Scrapling, use APIs only |
| `web_search_scrapling_enabled: false` | Disable Scrapling in all modes |

## Implementation Details

### File Changes

**src/jarvis/agent/tools.py**
- Added `from scrapling.fetchers import Fetcher` import (with graceful fallback if not installed)
- Added `_scrapling_web_search(query, max_lines)` helper function
- Updated `tool_web_search()` to attempt Scrapling before DuckDuckGo API
- All results include `"source"` field (scrapling, duckduckgo, google_news_rss, or none)

**src/jarvis/config.py**
- Added three new config keys: web_search_provider, web_search_scrapling_enabled, web_search_timeout
- Defaults: "auto" (provider), True (enabled), 8 (timeout)

**config/app.json**
- User-facing config file updated with web search settings
- Override defaults here to customize provider behavior

### CSS Selectors Used

Scrapling fetches DuckDuckGo HTML and extracts results via:
1. `.result__snippet::text` (primary selector)
2. `.result__body::text` (fallback selector)

Results limited to top 3 snippets, compacted to 2 lines for voice output.

## Error Handling

Scrapling gracefully degrades:

```python
# If Scrapling fails or unavailable
if not SCRAPLING_AVAILABLE or scrapling_fetch_error:
    # → Fall back to DuckDuckGo API
    # → Fall back to Google News RSS (if news-like query)
    # → Return "no concise web result found"
```

**Key safeguard:** If Scrapling is not installed, `SCRAPLING_AVAILABLE = False` and system uses APIs only (no crash).

## Usage Examples

### Voice Command (unchanged from user perspective)

```
User: "Search Python web scraping"
Jarvis: "Web Scraping - is the process of extracting data from websites automatically..."
        (source: scrapling)
```

### Programmatic Test

```python
from jarvis.agent.tools import tool_web_search

result = tool_web_search({"query": "latest AI news", "lines": 2}, None, None)
print(result["output"])  # 2-line summary
print(result["source"])  # "scrapling" or "duckduckgo" or "google_news_rss"
```

## Performance Notes

- **Scrapling latency:** ~1-3 seconds per fetch (includes browser context, CSS rendering)
- **DuckDuckGo API latency:** ~200-500ms per fetch (lightweight, no rendering)
- **Fallback overhead:** Negligible; only attempts next method on failure

**Recommendation:** Set `web_search_timeout: 8` to allow Scrapling time to fetch and render, then fall back if exceeded.

## Troubleshooting

### "Scrapling: No module named scrapling"
→ Run `pip install "scrapling[ai]"` then `scrapling install`

### "Scrapling returns empty results"
→ CSS selectors may have changed; system auto-falls back to DuckDuckGo API (expected behavior)

### "Playwright browser install failed"
→ Run `scrapling install` manually; may require sudo for system dependencies

### "Scrapling timeout exceeded"
→ Increase `web_search_timeout` in config/app.json or set `web_search_provider: "duckduckgo"` to skip

## Future Enhancements

- [ ] MCP server integration (use Scrapling as Groq-compatible tool)
- [ ] Custom CSS selector configuration per domain
- [ ] Caching layer for repeated queries
- [ ] Rate-limiting per domain to avoid blocks
- [ ] Telemetry: track source usage and success rates

---

**Last Updated:** April 12, 2026
**Scrapling Version:** 0.4.5
**Status:** ✅ Integrated, tested, fallback-safe
