"""Per-session rolling context: Redis when reachable, in-process dict otherwise."""

from __future__ import annotations

import copy
import json
from typing import Any

from loguru import logger

MAX_HOPS = 64  # hard cap per session; the classifier only reads the last few


def new_state() -> dict[str, Any]:
    return {
        "hop": 0,
        "goal": None,          # first user message; never overwritten by agent output
        "trusted": [],         # indicators (emails, urls, ids) present in user/system text
        "taint": {},           # indicator -> {"hop", "source", "risk"}  (untrusted origin)
        "sensitivity": 0.0,    # raised by every FLAG, boosts later risk
        "suspended": [],       # "source->target" channels shut by a BLOCK
        "tools": {},           # agent -> tool names seen (behavioural baseline)
        "lens": {},            # agent -> [count, mean content length]
        "cues": 0,             # untrusted events so far that contained instruction-like text
        "claims": 0,           # authority / pre-approval claims made by untrusted events so far
    }


class MemoryStore:
    kind = "memory"

    def __init__(self) -> None:
        self._hops: dict[str, list[dict]] = {}
        self._state: dict[str, dict] = {}

    def hops(self, sid: str) -> list[dict]:
        return list(self._hops.get(sid, []))

    def push(self, sid: str, hop: dict) -> None:
        self._hops.setdefault(sid, []).append(hop)
        del self._hops[sid][:-MAX_HOPS]

    def state(self, sid: str) -> dict:
        return copy.deepcopy(self._state.get(sid) or new_state())

    def save(self, sid: str, state: dict) -> None:
        self._state[sid] = state

    def drop(self, sid: str) -> None:
        self._hops.pop(sid, None)
        self._state.pop(sid, None)

    def sessions(self) -> list[str]:
        return list(self._state)


class RedisStore:
    kind = "redis"

    def __init__(self, client, ttl: int) -> None:
        self.r, self.ttl = client, ttl

    def _k(self, sid: str, part: str) -> str:
        return f"mapis:{sid}:{part}"

    def hops(self, sid: str) -> list[dict]:
        return [json.loads(x) for x in self.r.lrange(self._k(sid, "hops"), 0, -1)]

    def push(self, sid: str, hop: dict) -> None:
        key = self._k(sid, "hops")
        pipe = self.r.pipeline()
        pipe.rpush(key, json.dumps(hop))
        pipe.ltrim(key, -MAX_HOPS, -1)
        pipe.expire(key, self.ttl)
        pipe.execute()

    def state(self, sid: str) -> dict:
        raw = self.r.get(self._k(sid, "state"))
        return json.loads(raw) if raw else new_state()

    def save(self, sid: str, state: dict) -> None:
        self.r.set(self._k(sid, "state"), json.dumps(state), ex=self.ttl)

    def drop(self, sid: str) -> None:
        self.r.delete(self._k(sid, "hops"), self._k(sid, "state"))

    def sessions(self) -> list[str]:
        return sorted({k.split(":")[1] for k in self.r.scan_iter("mapis:*:state")})


def make_store(redis_url: str | None, ttl: int = 3600):
    """Redis if it answers a ping within 0.5 s, otherwise the in-memory store (logged)."""
    if redis_url:
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=0.5)
            client.ping()
            return RedisStore(client, ttl)
        except Exception as exc:  # noqa: BLE001 - any failure means "no Redis"
            logger.warning(f"Redis unavailable ({exc.__class__.__name__}); using in-memory session store")
    return MemoryStore()
