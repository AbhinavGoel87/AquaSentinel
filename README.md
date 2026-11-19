# Kshetra

Autonomous precision irrigation and crop monitoring.

**Every drop matters. Every crop counts.**

The same Python app runs on Windows, macOS, and Linux. Moisture and the doctor rover's position in this build are simulated. The page says so. Nothing here is a calibrated field measurement, and water use is intentionally not shown yet.

## What this build does

- Shows two irrigation zones, six soil sensors, and one doctor rover on the road between the beds. The docking station is at the south end of that road.
- Turns a sprinkler on when its zone is dry and two sensors agree. Turns it off at the target, at 10 minutes, on emergency stop, or when the program starts again.
- Compares a plant photo with the pictures in `plant_database` and tells the farmer whether the closest match is healthy, a deficiency, a disease, a discrepancy, or too uncertain to decide.
- Adds a CoLeaf nutrient to the irrigation tank only after the farmer confirms, and only for a short timed cycle. The mixed group cannot start a treatment.
- Saves readings, sprinkler events, photos, doctor reports, and treatment events in a SQLite file.

The photo match is the closest example picture in the CoLeaf set: about 1,000 coffee-leaf photos in ten groups. It is not a lab test and it does not measure a nutrient. See `plant_database/README.md` to install the zip.

## Run it

From this folder. You need Python 3.11 through 3.15. The first start creates `.venv`, updates pip, and installs the packages. The page is the same on every system: tabs for the field, the doctor, the sensors, and the alerts.

Windows:

```text
py -3 start.py
```

macOS and Linux:

```text
python3 start.py
```

On a Mac, if `python3` is not found, install Python from python.org and open a new Terminal window.

Open http://127.0.0.1:5000

The server listens on this computer only. Leave `KSHETRA_HOST` unset unless you mean to share it. Stop the program with Ctrl+C.

Zone 1 starts dry, so its sprinkler turns on by itself. Field time runs at 60×, so the movement is a demo setting, not real soil physics. A sprinkler closes itself after 10 minutes of computer time.

## Reset the field

Sensor starting values in `data/field.json` apply to a new database. After the first run, moisture continues from the last saved reading.

Delete these files to start the story again:

```text
data/kshetra.db
data/kshetra.db-wal
data/kshetra.db-shm
```

You can edit setpoints, drying rates, and the safety limit in `data/field.json`. Put leaf photos and the farmer's instructions in `plant_database/entries`. Restart the program after either change.

## Tests

With the virtual environment active, from this folder:

Windows: `py -3 -m unittest discover -s tests -v`

macOS and Linux: `python3 -m unittest discover -s tests -v`

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `KSHETRA_HOST` | `127.0.0.1` | Bind address |
| `KSHETRA_PORT` | `5000` | Port |
| `KSHETRA_DB` | `data/kshetra.db` | SQLite file |
| `KSHETRA_FIELD` | `data/field.json` | Field description |
| `KSHETRA_PLANT_DB` | `plant_database` | Folder of example plant photos |
| `KSHETRA_TICK_SECONDS` | `1` | Seconds of computer time between simulator steps |

Field time scale, sensor rates, and the two-sensor rule live in `data/field.json`.

## Safety choices already in force

- Sprinklers start closed every time the program launches.
- An open sprinkler has a maximum real-world duration.
- Emergency stop holds the sprinklers closed and stops a treatment until a person resets it. Reset does not open them.
- A treatment never starts from an uncertain photo, and it never runs longer than three minutes.
- ESP32 sketches leave every output pin at `-1` until you set the real wiring. Those pins are not driven.

## More detail

- `docs/ARCHITECTURE.md` — how the pieces fit, and what we changed from the first plan
- `docs/DATA_CONTRACTS.md` — database tables and the reserved MQTT messages
- `docs/STATUS.md` — what is done and what is next
