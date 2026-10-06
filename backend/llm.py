"""Minimal OpenAI-compatible chat client for the LLM baselines and the live-agent run.

Works with any provider that speaks the OpenAI chat API: Groq, Cerebras, Gemini (OpenAI endpoint), OpenRouter, OpenAI, or a local
Ollama server. Configured by environment variables so no key is ever written to the repository:

    LLM_BASE_URL   e.g. https://api.groq.com/openai/v1   |  http://localhost:11434/v1 (Ollama)
    LLM_API_KEY    the provider key (any string for Ollama)
    LLM_MODEL      e.g. llama-3.3-70b-versatile          |  qwen2.5:7b
    LLM_RPM        optional client-side requests-per-minute cap (free tiers), default 25

Every completion is cached on disk (results/llm_cache/<model>.jsonl, keyed by a hash of the request) so an interrupted run resumes
for free and reruns cost nothing. 429 / 5xx responses are retried with exponential backoff.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LLMClient:
    def __init__(self, model: str | None = None, base_url: str | None = None, api_key: str | None = None, cache: bool = True):
        from openai import OpenAI

        self.model = model or os.environ.get("LLM_MODEL") or "llama-3.3-70b-versatile"
        self.base_url = base_url or os.environ.get("LLM_BASE_URL") or "https://api.groq.com/openai/v1"
        key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY") or "none"
        self.client = OpenAI(base_url=self.base_url, api_key=key, max_retries=0, timeout=120)
        self.min_interval = 60.0 / float(os.environ.get("LLM_RPM", "25"))
        self._last, self._lock = 0.0, threading.Lock()
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in self.model)
        self.cache_path = ROOT / "results" / "llm_cache" / f"{safe}.jsonl" if cache else None
        self._cache: dict[str, dict] = {}
        if self.cache_path and self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._cache[row["key"]] = row
        self.calls = self.cached = 0

    def _key(self, messages: list[dict], **kw) -> str:
        return hashlib.sha256(json.dumps([self.model, messages, kw], sort_keys=True).encode()).hexdigest()

    def chat(self, messages: list[dict], max_tokens: int = 200, temperature: float = 0.0, **kw) -> tuple[str, float]:
        """-> (reply text, latency ms of the real call; the cached latency when served from cache)."""
        key = self._key(messages, max_tokens=max_tokens, temperature=temperature, **kw)
        if key in self._cache:
            self.cached += 1
            return self._cache[key]["text"], self._cache[key]["ms"]
        delay = 4.0
        for attempt in range(8):
            with self._lock:
                wait = self._last + self.min_interval - time.time()
                if wait > 0:
                    time.sleep(wait)
                self._last = time.time()
            try:
                t0 = time.perf_counter()
                resp = self.client.chat.completions.create(model=self.model, messages=messages, max_tokens=max_tokens, temperature=temperature, **kw)
                ms = 1000 * (time.perf_counter() - t0)
                text = resp.choices[0].message.content or ""
                break
            except Exception as exc:  # rate limits and transient server errors
                status = getattr(exc, "status_code", None)
                if status not in (None, 408, 409, 429, 500, 502, 503, 504) or attempt == 7:
                    raise
                print(f"[llm] {type(exc).__name__} {status}; retrying in {delay:.0f}s")
                time.sleep(delay)
                delay = min(delay * 2, 120)
        self.calls += 1
        row = {"key": key, "text": text, "ms": round(ms, 1)}
        self._cache[key] = row
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return text, ms
