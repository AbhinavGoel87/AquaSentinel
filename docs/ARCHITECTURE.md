# Architecture

Kshetra is a local controller for three irrigation zones, nine soil sensors, and two inspection rovers. The browser talks only to Flask. Flask asks sensor health and valve safety. Those layers talk to the simulator today. Later they can talk to MQTT and HTTP hardware without a new dashboard.

```text
Field page
    |
Flask REST
    |
Sensor health + valve safety
    |                 (Phase 2 decisions, Phase 3 rovers, Phase 4 images sit here)
SQLite
    |
Simulator now  -->  MQTT / HTTP devices later
```

Valve safety is the only door that can open a zone. The future irrigation engine may request water. It may not skip the time limit, the emergency stop, or the closed-on-startup rule.

## Decisions

- **Flask and SQLite.** They are enough for the exhibition, readable for this team, and they run on a Raspberry Pi later.
- **No broker yet.** Topic names and JSON shapes are fixed and tested. Phase 6 can put MQTT behind the same method names: `snapshot`, `set_valve`, `emergency_stop`, `reset_emergency`.
- **Two clocks.** Field moisture uses accelerated time so a booth demo can show drying and watering. The valve limit uses computer time, because a real solenoid cares about real seconds. The default acceleration is 60× and the page says so.
- **Two agreeing sensors.** A zone average needs at least two usable readings. If one sensor is far from the other two, and those two agree, the odd one is shown and excluded. The gap is 20 points and the agreement band is 10 points in `data/field.json`. These are engineering defaults, not a soil study.
- **Water is absent on purpose.** A litres column exists so a later estimate has a home. This phase writes nothing there.
- **Images and status travel differently.** Future photos use HTTP `POST /api/inspections`. MQTT is for short status and commands. That path is reserved and not served yet.
- **localhost.** The server binds to `127.0.0.1` unless you change it.

## Hardware assumptions, not purchases

Correct these before firmware is written if the kit differs.

- One shared pump and three normally-closed solenoid valves. The pump may run only while a valve is open. That interlock arrives with automatic irrigation.
- The Pi will not read analog pins. Sensor boards will publish numbers. The ADC part stays unnamed until the moisture sensor model is known.
- Each rover is a motion ESP32 plus a separate ESP32-CAM. Motors get their own power supply. If the kit can only use one board, we count pins before writing motion code.
- Navigation is tape and checkpoints. The two lanes in `data/field.json` are not allowed to share a point.
- If a controller later misses its heartbeat, valves close, the pump stays off, and a rover stops. It does not keep driving.

GPIO numbers, valve voltage, and motor-driver model are unknown. They are not guessed in code.

## What "simulated" means here

Each sensor has a starting moisture, a drying rate, and a faster rise while its zone valve is open. A little noise makes the trace move. Calibration scale and offset are applied before the health check. The default calibration is identity: scale 1, offset 0. That is a hook for a real calibration, not a claim that one has been done.

Rover markers stay at their docks. Battery and camera are not given fake numbers.

## Folder map

`backend/simulation` moves the field. `backend/sensors` judges readings. `backend/irrigation` refuses unsafe valve commands. `backend/communication` holds topic names and message checks. `backend/hardware` names the methods a future adapter must offer. `backend/database` is SQLite. `frontend` is the field page. `firmware` is a safety note only. `models` is empty because there is no trained model yet.
