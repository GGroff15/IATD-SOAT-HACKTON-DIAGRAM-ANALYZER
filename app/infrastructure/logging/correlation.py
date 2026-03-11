import contextvars
from typing import Optional

_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def clear_correlation_id() -> None:
    _correlation_id.set(None)
