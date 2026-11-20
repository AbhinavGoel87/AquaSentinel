# Kshetra

The plant doctor for this computer.

The field, its soil sensors, and the Arduino Uno are a separate system. This app does not connect to them. There is no Bluetooth link and no sprinkler control here.

The same Python app runs on Windows, macOS, and Linux. An ESP32-CAM on the same Wi-Fi posts a JPEG. This computer compares that photo with the pictures in `plant_database` and shows the closest example.

## What this build does

- Receives a plant photo from the ESP32-CAM, or from the file picker on the page.
- Compares it with the example pictures and says whether the closest match is healthy, a deficiency, a discrepancy, or too uncertain to decide.
- Saves the photo and the report in a SQLite file.

The photo match is the closest example picture in the CoLeaf set: about 1,000 coffee-leaf photos in ten groups. It is not a lab test and it does not measure a nutrient. **Add to irrigation** records a short timer on this computer. It does not open a valve or talk to the Arduino Uno. See `plant_database/README.md` to install the zip.

## Run it

From this folder. You need Python 3.11 through 3.15. The first start creates `.venv`, updates pip, and installs the packages. The page is the doctor.

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

The server listens on this computer only. Leave `KSHETRA_HOST` unset unless the ESP32-CAM must reach this computer. For that, set `KSHETRA_HOST` to `0.0.0.0` and put the computer's Wi-Fi address in `firmware/rover_doctor/rover_doctor.ino`. Stop the program with Ctrl+C.

## Reset the doctor

Delete these files to clear saved photos and reports:

```text
data/kshetra.db
data/kshetra.db-wal
data/kshetra.db-shm
```

Put leaf photos and the farmer's instructions in `plant_database/entries`. Restart the program after a change.

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
| `KSHETRA_PLANT_DB` | `plant_database` | Folder of example plant photos |

## Safety choices already in force

- This app does not open a valve, run a pump, or talk to the Arduino Uno.
- An uncertain photo does not name a treatment.
- The ESP32-CAM sketch leaves motor pins at `-1` until you set real wiring. Those pins are not driven.

## More detail

- `docs/ARCHITECTURE.md` — how the pieces fit, and what we changed from the first plan
- `docs/DATA_CONTRACTS.md` — database tables and the reserved MQTT messages
- `docs/STATUS.md` — what is done and what is next
