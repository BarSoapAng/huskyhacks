from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal


DebounceStatus = Literal["started", "pending", "expired"]


@dataclass(frozen=True)
class DebounceState:
    normalized_url: str
    started_at: datetime
    expires_at: datetime


class DebounceService:
    def __init__(self, window_seconds: int = 30) -> None:
        self._window = timedelta(seconds=window_seconds)
        self._states: dict[str, DebounceState] = {}

    def check(self, normalized_url: str) -> DebounceStatus:
        now = datetime.now(UTC)
        self._prune_expired(now)

        key = normalized_url
        state = self._states.get(key)

        if state is None:
            self._states[key] = DebounceState(
                normalized_url=normalized_url,
                started_at=now,
                expires_at=now + self._window,
            )
            return "started"

        if now < state.expires_at:
            return "pending"

        return "expired"

    def _prune_expired(self, now: datetime) -> None:
        expired_keys = [
            key
            for key, state in self._states.items()
            if now >= state.expires_at + self._window
        ]
        for key in expired_keys:
            del self._states[key]


debounce_service = DebounceService()
