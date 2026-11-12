"""The only door that may open a valve.

Later irrigation logic may request water. It still has to pass these checks.
Times here are wall-clock seconds, because a real solenoid cares about real time.
"""

from __future__ import annotations


class SafetyError(Exception):
    """A valve command was refused."""


def open_is_allowed(emergency: bool) -> tuple[bool, str]:
    if emergency:
        return False, "Emergency stop is latched. Reset it before opening a valve."
    return True, ""


def valve_should_force_close(
    open_seconds: float,
    max_seconds: int,
    emergency: bool,
) -> tuple[bool, str | None]:
    if emergency:
        return True, "emergency_stop"
    if open_seconds >= max_seconds:
        return True, "max_duration"
    return False, None
