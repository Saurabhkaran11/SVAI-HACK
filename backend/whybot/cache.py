"""Tiny thread-safe TTL cache for expensive answers (LLM + graph queries).

Keys include the brain's state.version, so any new doc or memory invalidates naturally.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable

from .config import settings


class TTLCache:
    def __init__(self, ttl_s: int, max_items: int = 256):
        self.ttl, self.max = ttl_s, max_items
        self._data: OrderedDict[tuple, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    def get_or_set(self, key: tuple, fn: Callable[[], Any]) -> tuple[Any, bool]:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item and now - item[0] < self.ttl:
                self._data.move_to_end(key)
                self.hits += 1
                return item[1], True
        value = fn()  # computed outside the lock so slow LLM calls don't block others
        with self._lock:
            self.misses += 1
            self._data[key] = (now, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max:
                self._data.popitem(last=False)
        return value, False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def stats(self) -> dict:
        return {"items": len(self._data), "hits": self.hits, "misses": self.misses}


answers = TTLCache(settings.cache_ttl_s)
