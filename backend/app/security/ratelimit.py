"""
Basit, bellek içi istek sınırlayıcı (IP + uç başına, kayan pencere).

Prototip içindir: tek süreçte çalışır. Çok sunuculu kurulumda Redis gibi ortak
bir depo gerekir (yol haritasında).
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.config import settings

_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = Lock()


def reset() -> None:
    with _lock:
        _hits.clear()


def limit(request: Request) -> None:
    per_min = settings.rate_limit_per_min
    if per_min <= 0:
        return
    ip = request.client.host if request.client else "?"
    key = (ip, request.url.path)
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= per_min:
            raise HTTPException(status_code=429, detail="rate_limited")
        q.append(now)
