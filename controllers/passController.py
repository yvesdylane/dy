import random
import threading
from datetime import datetime, timedelta, timezone

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
POOL_SIZE = 16
CODE_TTL_SECONDS = 60

_pool: dict[str, datetime] = {}
_lock = threading.Lock()


def _generate_code(existing: set[str] | None = None) -> str:
    seen = existing if existing is not None else set()
    while True:
        code = "".join(random.choices(CODE_ALPHABET, k=5))
        if code not in seen:
            seen.add(code)
            return code


def start_pass() -> list[dict]:
    global _pool
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=CODE_TTL_SECONDS)
    seen: set[str] = set()
    codes = []
    with _lock:
        _pool.clear()
        for _ in range(POOL_SIZE):
            code_str = _generate_code(seen)
            _pool[code_str] = expires_at
            codes.append({"code": code_str, "expires_at": expires_at.isoformat()})
    return codes


def get_active_codes() -> list[dict]:
    now = datetime.now(timezone.utc)
    with _lock:
        expired = [c for c, exp in _pool.items() if exp <= now]
        for c in expired:
            del _pool[c]
        while len(_pool) < POOL_SIZE:
            code_str = _generate_code(set(_pool.keys()))
            exp = datetime.now(timezone.utc) + timedelta(seconds=CODE_TTL_SECONDS)
            _pool[code_str] = exp
        result = [
            {"code": c, "expires_at": exp.isoformat()}
            for c, exp in _pool.items()
        ]
    return result


def stop_pass() -> None:
    with _lock:
        _pool.clear()


def use_code(code_str: str) -> bool:
    """Validate and consume a pass code. Returns True if valid."""
    now = datetime.now(timezone.utc)
    with _lock:
        exp = _pool.get(code_str)
        if exp is None:
            return False
        if exp <= now:
            del _pool[code_str]
            return False
        del _pool[code_str]
    return True
