"""When a sprinkler may run.

Dry soil can start a sprinkler only when two sensors agree.
The sprinkler stops at the target, when the sensors stop agreeing,
or when valve safety hits the time limit or the emergency stop.
"""

from __future__ import annotations


def sprinkler_action(
    *,
    status: str,
    average: float | None,
    low: float,
    target: float,
    valve_open: bool,
    seconds_since_close: float | None,
    cooldown_sec: int,
    emergency: bool,
) -> str:
    if emergency:
        return "hold"
    if valve_open and status != "ok":
        return "close_unsafe"
    if valve_open and average is not None and average >= target:
        return "close_target"
    if valve_open:
        return "hold"
    if status != "ok" or average is None or average >= low:
        return "hold"
    if seconds_since_close is not None and seconds_since_close < cooldown_sec:
        return "hold"
    return "open"
