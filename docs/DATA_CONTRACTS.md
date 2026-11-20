# Data contracts

The running app stores plant photos, doctor reports, and a confirmed timer. It does not start an MQTT broker and it does not open a valve.

The tables and topic names below belong to the unused field library. They are not served by the current page.

The computer's receive time is the time stored as `recorded_at`. A future device timestamp can be kept beside it so clock drift is visible. Field time (`sim_time`) is the accelerated demo clock.

## Tables

### zones

Identity and settings for Zone 1, Zone 2, and Zone 3: name, crop label, low setpoint, target moisture, maximum valve time, cooldown, mode, and whether the valve record is open.

Cooldown and automatic mode are stored for Phase 2. This build does not enforce cooldown and does not water by itself. Startup sets every `valve_open` back to 0.

### sensors

Identity, zone, map position, calibration offset, and calibration scale. The current reading is not stored on this row.

### sensor_readings

One saved sample: raw value, value after calibration, quality (`ok`, `suspect`, `missing`, `invalid`), source (`simulated` or later `hardware`), computer time, and simulated field time.

A missing sample stores nulls. An ok or suspect sample must sit between 0 and 100. Samples are written about every 30 seconds of computer time. The live page also keeps a short trace in memory between those saves.

Zone averages are calculated when the page asks for them. They are not copied into another table.

### irrigation_events

One row each time a valve opens: zone, mode, reason, start, end, stop reason, and duration in wall-clock seconds.

`estimated_liters` must stay null until a later build stores an explicit estimate or a meter reading. Stop reasons used now are `manual`, `max_duration`, `emergency_stop`, and `startup_safe_state`.

### alerts

A warning or a danger with a stable code, a message, a source, and an acknowledgement time. The page shows alerts that are not yet acknowledged. A recovered sensor acknowledges its own open alert.

## MQTT topics

Not connected in this phase. Commands and emergency stop are QoS 1. Measurements and heartbeats are QoS 0. Rover status and emergency stop should be retained.

| Topic | Direction | Body |
| --- | --- | --- |
| `kshetra/sensors/zone1` | Sensor board to controller | Sensor batch. `zone2` and `zone3` match. |
| `kshetra/irrigation/zone1` | Controller to valve board | Valve command. `zone2` and `zone3` match. |
| `kshetra/rover1/status` | Rover to controller | Rover status. `rover2` matches. |
| `kshetra/rover1/command` | Controller to rover | Movement command. `rover2` matches. |
| `kshetra/system/heartbeat` | Device to controller | Device id and time. |
| `kshetra/system/estop` | Controller to devices | Latch emergency stop. |

Photos will use `POST /api/inspections` over HTTP, with the rover id, checkpoint, time, and image file. That address is reserved. This phase returns "not part of this build" if you call it.

## Sensor batch

```json
{
  "device_id": "esp32-zone1",
  "source": "simulated",
  "ts": "2026-11-11T12:00:00Z",
  "seq": 1,
  "zone_id": "zone1",
  "readings": [
    {"sensor_id": "zone1-s1", "moisture_pct": 34.2, "ok": true}
  ]
}
```

`source` is `simulated` or `hardware`. `seq` is a non-negative integer. When `ok` is false, `moisture_pct` is null. When `ok` is true, moisture is a number from 0 to 100.

## Valve command

```json
{
  "command_id": "cmd-1",
  "device_id": "pi-controller",
  "ts": "2026-11-11T12:00:00Z",
  "zone_id": "zone1",
  "valve": "open",
  "mode": "manual",
  "max_seconds": 600
}
```

`valve` is `open` or `closed`. `mode` is `manual` or `automatic`. `max_seconds` is an integer from 1 to 3600. The controller still applies its own safety limit if the command asks for longer than the zone allows.

## Rover status

```json
{
  "device_id": "rover1",
  "source": "simulated",
  "ts": "2026-11-11T12:00:00Z",
  "seq": 4,
  "state": "idle",
  "battery_pct": 80,
  "camera_ok": true,
  "link_ok": true,
  "route_id": "route-west",
  "checkpoint_id": null
}
```

`state` is `idle`, `moving`, `inspecting`, `returning`, or `error`. `checkpoint_id` may be null while the rover is at its dock.

The checks live in `backend/communication/schemas.py`. A message that passes has the right shape. It is not evidence that a sensor was calibrated.
