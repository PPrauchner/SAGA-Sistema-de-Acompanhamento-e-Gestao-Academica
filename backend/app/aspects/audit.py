"""
Aspecto A02 — Auditoria das Operações (Around advice).
"""

from functools import wraps
from backend.app.aspects.aspect_config import AUDIT_ENABLED


def audit_operation(func):
    """Aspecto A02 — Auditoria das Operações."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not AUDIT_ENABLED:
            return await func(*args, **kwargs)
        
        # TODO: Implement full audit logic
        print(f"AUDIT: Executing {func.__name__}")
        return await func(*args, **kwargs)
    return wrapper
