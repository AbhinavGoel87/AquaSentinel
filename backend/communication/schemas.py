"""Structural checks for the messages devices will exchange.

A passing check means the JSON has the right shape. It does not mean a
sensor was calibrated or that a valve moved in the field.
"""

from __future__ import annotations

from datetime import datetime

ROVER_STATES = ("idle", "moving", "inspecting", "returning", "error")


def validate_sensor_report(message: dict) -> list[str]:
    if not isinstance(message, dict):
        return ["Message must be a JSON object."]
    errors = _require(message, ("device_id", "source", "ts", "seq", "zone_id", "readings"))
    if errors:
        return errors
    errors.extend(_device_fields(message))
    errors.extend(_sequence(message.get("seq")))
    readings = message.get("readings")
    if not isinstance(readings, list) or not readings:
        errors.append("readings must be a non-empty list.")
        return errors
    for index, reading in enumerate(readings):
        errors.extend(_reading(index, reading))
    return errors


def validate_valve_command(message: dict) -> list[str]:
    if not isinstance(message, dict):
        return ["Message must be a JSON object."]
    errors = _require(
        message,
        ("command_id", "device_id", "ts", "zone_id", "valve", "mode", "max_seconds"),
    )
    if errors:
        return errors
    if not isinstance(message["command_id"], str) or not message["command_id"]:
        errors.append("command_id must be a non-empty string.")
    if not isinstance(message["device_id"], str) or not message["device_id"]:
        errors.append("device_id must be a non-empty string.")
    if not _is_iso(message.get("ts")):
        errors.append("ts must be an ISO-8601 timestamp.")
    if not isinstance(message["zone_id"], str) or not message["zone_id"]:
        errors.append("zone_id must be a non-empty string.")
    if message["valve"] not in ("open", "closed"):
        errors.append("valve must be 'open' or 'closed'.")
    if message["mode"] not in ("manual", "automatic"):
        errors.append("mode must be 'manual' or 'automatic'.")
    limit = message["max_seconds"]
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 3600:
        errors.append("max_seconds must be an integer from 1 to 3600.")
    return errors


def validate_rover_status(message: dict) -> list[str]:
    if not isinstance(message, dict):
        return ["Message must be a JSON object."]
    errors = _require(
        message,
        (
            "device_id",
            "source",
            "ts",
            "seq",
            "state",
            "battery_pct",
            "camera_ok",
            "link_ok",
            "route_id",
            "checkpoint_id",
        ),
    )
    if errors:
        return errors
    errors.extend(_device_fields(message))
    errors.extend(_sequence(message.get("seq")))
    if message["state"] not in ROVER_STATES:
        errors.append("state must be idle, moving, inspecting, returning, or error.")
    battery = message["battery_pct"]
    if isinstance(battery, bool) or not isinstance(battery, (int, float)) or not 0 <= float(battery) <= 100:
        errors.append("battery_pct must be a number from 0 to 100.")
    if not isinstance(message["camera_ok"], bool):
        errors.append("camera_ok must be a boolean.")
    if not isinstance(message["link_ok"], bool):
        errors.append("link_ok must be a boolean.")
    if not isinstance(message["route_id"], str) or not message["route_id"]:
        errors.append("route_id must be a non-empty string.")
    checkpoint = message["checkpoint_id"]
    if checkpoint is not None and not isinstance(checkpoint, str):
        errors.append("checkpoint_id must be a string or null.")
    return errors


def _require(message: dict, keys: tuple[str, ...]) -> list[str]:
    return [f"Missing '{key}'." for key in keys if key not in message]


def _device_fields(message: dict) -> list[str]:
    errors = []
    if not isinstance(message.get("device_id"), str) or not message.get("device_id"):
        errors.append("device_id must be a non-empty string.")
    if message.get("source") not in ("simulated", "hardware"):
        errors.append("source must be 'simulated' or 'hardware'.")
    if not isinstance(message.get("zone_id", "zone1"), str):
        errors.append("zone_id must be a string.")
    if "zone_id" in message and (not isinstance(message["zone_id"], str) or not message["zone_id"]):
        errors.append("zone_id must be a non-empty string.")
    if not _is_iso(message.get("ts")):
        errors.append("ts must be an ISO-8601 timestamp.")
    return errors


def _sequence(value) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return ["seq must be a non-negative integer."]
    return []


def _reading(index: int, reading) -> list[str]:
    prefix = f"readings[{index}]"
    if not isinstance(reading, dict):
        return [f"{prefix} must be an object."]
    errors = []
    for key in ("sensor_id", "moisture_pct", "ok"):
        if key not in reading:
            errors.append(f"{prefix} missing '{key}'.")
    if errors:
        return errors
    if not isinstance(reading["sensor_id"], str) or not reading["sensor_id"]:
        errors.append(f"{prefix}.sensor_id must be a non-empty string.")
    if not isinstance(reading["ok"], bool):
        errors.append(f"{prefix}.ok must be a boolean.")
        return errors
    moisture = reading["moisture_pct"]
    if reading["ok"]:
        if isinstance(moisture, bool) or not isinstance(moisture, (int, float)):
            errors.append(f"{prefix}.moisture_pct must be a number when ok is true.")
        elif not 0 <= float(moisture) <= 100:
            errors.append(f"{prefix}.moisture_pct must be between 0 and 100.")
    elif moisture is not None:
        errors.append(f"{prefix}.moisture_pct must be null when ok is false.")
    return errors


def _is_iso(value) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
