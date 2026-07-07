import random
import threading
from datetime import datetime, timedelta, timezone

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
POOL_SIZE = 16
CODE_TTL_SECONDS = 60

_pool: dict[str, tuple[datetime, str]] = {}
_current_mode: str = "entry"
_lock = threading.Lock()


def _generate_code(existing: set[str] | None = None) -> str:
    seen = existing if existing is not None else set()
    while True:
        code = "".join(random.choices(CODE_ALPHABET, k=5))
        if code not in seen:
            seen.add(code)
            return code


def start_pass(mode: str = "entry") -> list[dict]:
    global _pool, _current_mode
    _current_mode = mode
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=CODE_TTL_SECONDS)
    seen: set[str] = set()
    codes = []
    with _lock:
        _pool.clear()
        for _ in range(POOL_SIZE):
            code_str = _generate_code(seen)
            _pool[code_str] = (expires_at, mode)
            codes.append({
                "code": code_str,
                "expires_at": expires_at.isoformat(),
                "mode": mode,
            })
    return codes


def get_active_codes() -> list[dict]:
    now = datetime.now(timezone.utc)
    with _lock:
        expired = [c for c, (exp, _) in _pool.items() if exp <= now]
        for c in expired:
            del _pool[c]
        while len(_pool) < POOL_SIZE:
            code_str = _generate_code(set(_pool.keys()))
            exp = datetime.now(timezone.utc) + timedelta(seconds=CODE_TTL_SECONDS)
            _pool[code_str] = (exp, _current_mode)
        result = [
            {"code": c, "expires_at": exp.isoformat(), "mode": md}
            for c, (exp, md) in _pool.items()
        ]
    return result


def stop_pass() -> None:
    with _lock:
        _pool.clear()


def use_code(code_str: str) -> tuple[bool, str | None]:
    """Validate and consume a pass code.
    Returns (valid, mode) or (False, None).
    """
    now = datetime.now(timezone.utc)
    with _lock:
        entry = _pool.get(code_str)
        if entry is None:
            return False, None
        exp, mode = entry
        if exp <= now:
            del _pool[code_str]
            return False, None
        del _pool[code_str]
    return True, mode
