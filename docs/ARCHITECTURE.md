# Architecture

Kshetra on this computer is a plant doctor. The field, its sensors, and the Arduino Uno are a separate system. This app does not connect to them.

```text
Browser or ESP32-CAM
        |
Flask on this computer
        |
Doctor  ->  plant_database color match
        |
SQLite  (photo, report, and a confirmed timer)
```

The browser loads one page. The ESP32-CAM posts a JPEG to `POST /api/inspections`. The doctor compares leaf color with the example pictures and stores a report. **Add to irrigation** writes a short timer for that report. Nothing in this path drives a pin, a valve, or a pump.

The server binds to `127.0.0.1` unless `KSHETRA_HOST` is set. The camera can reach the computer only when the bind address is `0.0.0.0` and both devices are on the same Wi-Fi.

Older field, valve, and rover modules remain in the repository as unused libraries. `run.py` does not start them.
