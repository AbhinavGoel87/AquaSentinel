"""Methods a device adapter must offer.

FieldSimulator provides these today. A MQTT adapter in Phase 6 must provide
the same four methods. The dashboard imports neither adapter directly.
"""

from __future__ import annotations

from typing import Protocol


class FieldPort(Protocol):
    def snapshot(self) -> dict:
        """Return the current field picture for the dashboard."""

    def set_valve(self, zone_id: str, open_valve: bool, reason: str) -> dict:
        """Open or close one zone after the safety checks."""

    def emergency_stop(self) -> dict:
        """Close every zone and latch the stop."""

    def reset_emergency(self) -> dict:
        """Clear the latch. Leave every valve closed."""
