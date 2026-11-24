import math
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: int, scope: str):
        self.max_calls = max_calls
        self.period = period_seconds
        self.scope = scope
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client_ip]
            while hits and now - hits[0] >= self.period:
                hits.popleft()
            if len(hits) >= self.max_calls:
                retry_after = math.ceil(self.period - (now - hits[0]))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Terlalu banyak percobaan. Coba lagi beberapa saat lagi.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = RateLimiter(max_calls=5, period_seconds=60, scope="login")
customer_access_limiter = RateLimiter(max_calls=20, period_seconds=60, scope="customer-access")
checkout_limiter = RateLimiter(max_calls=10, period_seconds=60, scope="checkout")
