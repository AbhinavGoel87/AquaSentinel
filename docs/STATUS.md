# Status

Phase 1 is the current build. Later phases are not started.

## Done

- Project layout, Flask app, and SQLite schema.
- Exhibition field file with 3 zones, 9 sensors, pipes, and 2 non-overlapping rover lanes.
- Moisture simulation on a labeled 60× clock, with different values at each sensor.
- Zone health: usable, suspect, missing, invalid, uneven, and insufficient.
- Manual virtual valves, 10-minute safety close, emergency stop, and closed-on-startup.
- Sensor-failure test control.
- Field page with the map, zone cards, sensor table, and alerts.
- Message checks and topic names for later MQTT.
- Unit and API tests.

## Not done

- Automatic irrigation, hysteresis, cooldown enforcement, and a labeled water estimate.
- Pump interlock.
- Rover movement, battery, camera, and checkpoint photos.
- Image upload, OpenCV, and the three-way crop label.
- The other dashboard sections: overview totals, analytics, and a settings screen.
- A running MQTT broker and device adapters.
- ESP32 firmware. The firmware folders explain the safety rules and contain no motor code.
- Raspberry Pi deployment.
- A trained model. `models/` is empty on purpose.

## Next

Phase 2: irrigation decisions. A zone may request water only when at least two sensors agree, the average is below its low setpoint, the valve is allowed, and the safety door accepts the request. It must stop at the target or at the time limit, then wait out the cooldown. Any litre figure must be labeled as an estimate.
