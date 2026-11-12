"""Reserved MQTT topic names.

Phase 1 does not open a broker. These strings are the contract Phase 6 will publish.
Commands and emergency stop use QoS 1. Frequent measurements use QoS 0.
Rover status and emergency stop should be retained so a reconnecting device
sees the latest order.
"""

from __future__ import annotations

HEARTBEAT_TOPIC = "aquasentinel/system/heartbeat"
ESTOP_TOPIC = "aquasentinel/system/estop"
INSPECTION_UPLOAD_PATH = "/api/inspections"


def sensor_topic(zone_id: str) -> str:
    return f"aquasentinel/sensors/{_token(zone_id)}"


def irrigation_topic(zone_id: str) -> str:
    return f"aquasentinel/irrigation/{_token(zone_id)}"


def rover_status_topic(rover_id: str) -> str:
    return f"aquasentinel/{_token(rover_id)}/status"


def rover_command_topic(rover_id: str) -> str:
    return f"aquasentinel/{_token(rover_id)}/command"


def _token(value: str) -> str:
    if not isinstance(value, str) or not value or any(character in value for character in ("/", " ", "#")):
        raise ValueError("Topic id must be a simple token.")
    return value
