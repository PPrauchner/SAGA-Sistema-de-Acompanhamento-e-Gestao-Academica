"""
Aspecto A03 — Histórico de Alterações (Before+After advice).
"""

from functools import wraps
from backend.app.aspects.aspect_config import HISTORY_ENABLED


def track_history(func):
    """Aspecto A03 — Histórico de Alterações."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not HISTORY_ENABLED:
            return await func(*args, **kwargs)
        
        # TODO: Implement full history tracking logic
        print(f"HISTORY: Tracking {func.__name__}")
        return await func(*args, **kwargs)
    return wrapper
