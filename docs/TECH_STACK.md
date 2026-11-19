# Kshetra tech stack

A guide for the builders. Written so a Grade 9 student can explain every choice to a judge, a teacher, or a parent.

No new code belongs with this note. The next coding step waits until we are told to go.

## What "tech stack" means

A tech stack is the set of languages, libraries, and tools a project uses, plus the reasons those choices fit the job. A language is what we write. A library is code someone else already wrote, which we call from our language. A protocol is a set of rules for how two machines send messages. Those three are different things, and mixing them up is how a project starts to sound more complicated than it is.

Kshetra needs five jobs:

1. Pretend the field is real, because the lab is closed.
2. Decide when a zone is dry, and refuse unsafe valve commands.
3. Remember what happened.
4. Show a farmer-style page on a laptop.
5. Leave a clean place where real ESP32 boards can connect later.

One main language can do jobs 1 to 3. The web page needs the three web languages. The circuit boards, later, need a different language. That is the whole stack.

## The short list

| Kind | Name | Used now? | Job in Kshetra |
| --- | --- | --- | --- |
| Language | Python 3.12 | Yes | Brain of the project: simulation, safety, database, web server, tests |
| Language | HTML | Yes | Structure of the field page |
| Language | CSS | Yes | How the page looks |
| Language | JavaScript | Yes | Live updates in the browser |
| Language | SQL | Yes | Questions we ask the database |
| Data format | JSON | Yes | The field description, and the shape of future device messages |
| Database | SQLite | Yes | The file that stores readings, valve events, and alerts |
| Library | Flask 3.1.3 | Yes | Lets the browser ask Python for the field |
| Language | C++ | Not yet | Future program inside each ESP32 |
| Protocol | HTTP | Yes, locally | How the page asks for data |
| Protocol | MQTT | Named, not running | Future radio-style messages for sensors, valves, and rovers |
| Library | OpenCV | Not yet | Future image preparation on the Pi |
| Library | TensorFlow Lite | Optional, later | A small trained model, only after we have real photos and a measured result |

The computer running this today is a Windows PC. It stands in for the Raspberry Pi. The same Python project is what we expect to copy onto the Pi when the lab opens. We have not done that copy yet.

## Look at it from six sides

### 1. As a student who has to understand the code

Python is the language to learn first. Almost every important decision lives there: how moisture changes, when a reading is ignored, when a valve must close. If you can read `backend/sensors/health.py` and `backend/irrigation/safety.py`, you can explain the science-fair logic without waving at the pictures.

HTML, CSS, and JavaScript are the page. You need enough of them to change words, colours, and what happens when a button is pressed. You do not need a website framework.

SQL is a small language inside the database. You do not write the whole project in it. You write sentences like "save this reading" and "give me the open alerts."

C++ can wait. Writing it now, with no board on the desk, would produce a sketch we must not flash onto a motor driver.

### 2. As a judge at the exhibition

A judge will trust a small stack you can explain. They will not trust a poster that lists TensorFlow, MQTT, GPS, and cloud AI if those pieces are not running.

What you can honestly say today:

- The page is HTML, CSS, and JavaScript.
- The controller is Python, using Flask.
- History is a SQLite file on this computer.
- The field is simulated. The page says so.
- Device message shapes are already written in Python and checked by tests. A broker is not connected.
- There is no trained plant-disease model in the project.

What you should not say:

- "The AI diagnosed a disease."
- "We measured a water saving."
- "The rovers are navigating." They are drawn at their docks.
- "MQTT is running." The topic names are reserved.

### 3. As the laptop now, and the Raspberry Pi later

Windows is the workshop. Python 3.12 is installed. Flask is the only package in `requirements.txt`. The database is a file, so there is no separate database server to install. The page loads from the same program. No account, no internet service, no CDN.

That matters at school. Exhibition Wi-Fi is unreliable. A project that needs a cloud login can fail on the morning of the fair. This one needs the laptop, Python, and a browser.

The Pi is a later home for the same Python program. We chose tools that exist on Raspberry Pi OS: Python, SQLite, Flask, and later OpenCV. We did not choose tools that are painful on a 4 GB Pi, such as a full TensorFlow install beside a camera and a web server.

### 4. As a safety engineer

The dangerous parts of this project are water and motors, not the web page. The stack supports a few safety rules that are already in the Python:

- Valves start closed every time the program launches.
- A valve cannot stay open past a real-time limit.
- Emergency stop latches until a person resets it. Reset does not open the valves.
- Two rover lanes are rejected if they share a point.

The stack also refuses to pretend. Litres are not calculated yet. A column is reserved so that a future estimate cannot be mixed up with a meter reading. Firmware folders contain safety notes and no motor code. GPIO pin numbers are not in the software, because the real boards have not been confirmed.

### 5. As someone who might add "more impressive" tools

These were considered and left out on purpose.

| Tempting addition | Why it stays out |
| --- | --- |
| React, Vue, or Angular | A build step and a second language ecosystem for a single page. Plain JavaScript is enough. |
| Node.js as a second server | The brain is already Python. Two servers means two places for a bug to hide. |
| FastAPI or Django instead of Flask | FastAPI is a good tool. Flask is easier to read for this team, and the page is server-rendered plus one script. Django is a large framework for sites with users and admin panels. We have one local page. |
| PostgreSQL or MySQL | A separate database program to install and keep running. SQLite is one file, which is the right size for an exhibition. |
| Docker | Another tool to learn before the fair. The project runs with a virtual environment. |
| A cloud dashboard | The fair laptop must work with the network unplugged. |
| Chart.js from the internet | A library loaded from a CDN fails offline. Later charts will be files inside the project, or graphics we draw ourselves. The field page already draws its own traces. |
| Full TensorFlow now | Heavy, and there is no trained model. Shipping the library would invite an accuracy claim we cannot make. |
| GPS, SLAM, or ROS | The rovers follow tape. Those systems would replace the actual plan with a different project. |
| An MQTT broker in Phase 1 | Useful later. Right now it is a second program that can fail while we are still building the field. The topic names are already fixed so the broker can be added without renaming the dashboard. |

### 6. As the hardware that does not exist yet

When the boards arrive, the stack grows by a small amount, not by a rewrite.

- ESP32 motion boards and the sensor board: C++ in the Arduino IDE.
- ESP32-CAM: C++ as well, but pictures travel by HTTP upload, not by MQTT. Camera frames are too large and too frequent for the sensor topics.
- Messages for moisture, valve commands, rover status, heartbeats, and emergency stop: MQTT, using the topic names in `docs/DATA_CONTRACTS.md`.
- The Pi still runs the same Python program. It becomes the MQTT client and the place that receives photos.

If the kit has three separate pumps instead of one shared pump, or normally-open valves instead of normally-closed valves, we change the safety rules before any firmware is flashed. The web languages do not change.

## Each piece, explained

### Python 3.12

Python is the language of the controller. We write it in ordinary text files. The version on this machine is 3.12.

It is a good fit because the same language can simulate soil, check sensor health, talk to SQLite, and answer the browser. A team of two students can read it aloud. Raspberry Pi OS already ships with Python.

In this project Python is responsible for:

- moving simulated moisture forward in time
- deciding which sensors count toward a zone
- opening and closing virtual valves, and refusing unsafe opens
- saving history
- serving the page

Flask is not another language. It is a Python library. Version 3.1.3 is the one installed and pinned in `requirements.txt`, so a second computer gets the same Flask. Flask's job is small: when the browser asks for `/api/field`, Flask calls the simulator and sends back JSON.

Tests use `unittest`, which comes with Python. We did not add a separate test framework.

### HTML

HTML is the skeleton of the page. It names the regions: the title, the field map, the zone cards, the sensor table, the alerts, and the failure-test controls. It does not decide moisture and it does not open a valve by itself.

### CSS

CSS is the appearance: the dark green field-instrument colours, spacing, the phone layout, and type. The typefaces are ones already on a Windows laptop, so the page does not download a font. The layout stacks on a narrow screen.

### JavaScript

JavaScript is the only language that runs inside the browser. Every two seconds it asks Python for a fresh picture of the field and updates the numbers, the map, and the valve buttons. When you press Open valve, JavaScript sends that request to Python. Python decides whether the valve may open. The button does not change the moisture by itself.

There is no React and no build step. The browser runs `frontend/static/js/field.js` directly. That is a feature. You can open the file and read it.

### SQL and SQLite

SQL is the language of the database. SQLite is the program that understands it. For us, SQLite stores one file, `data/kshetra.db`. There is no password and no database server.

The tables hold zones, sensors, readings, irrigation events, and alerts. "How wet is Zone 1 right now?" is calculated in Python from the latest usable readings. We do not store that average again, because two copies drift apart.

### JSON

JSON is not a programming language. It is a way to write data as text. `data/field.json` is the editable description of the field: three zones, nine sensors, pipe lines, two rover lanes, and the safety numbers. Future ESP32 messages will be JSON as well, with fields such as `device_id`, `source`, and `moisture_pct`. Python checks those shapes even though no board is connected.

### HTTP

HTTP is the protocol the browser already speaks. Our page uses it locally, on `127.0.0.1`, which means "this computer only." The server does not advertise itself on the school network unless someone deliberately changes that setting.

### MQTT

MQTT is a protocol for short messages between devices. A sensor board publishes "here are my readings." The Pi publishes "close this valve." A small program called a broker carries the messages. We have chosen the topic names and tested the JSON shapes. We have not installed the broker. Saying the project "uses MQTT" is fair only if you add "the contract is written; the broker is a later phase."

### C++ and the Arduino IDE

C++ is the usual language for ESP32 boards in the Arduino IDE. It is in the plan because the real rovers and the sensor board will need a program of their own. It is not in the current build. The firmware folders explain boot-with-motors-off, stop-if-the-link-dies, and separate motor power. They do not contain a sketch.

### OpenCV and TensorFlow Lite

OpenCV is a Python library for pictures: open a file, resize it, check if it is blurry or too dark. That belongs with rover photos, which we do not have yet.

TensorFlow Lite is a way to run a small trained model on a Pi. It is optional. A demonstration classifier with three honest labels can come first: apparently healthy, potentially abnormal, or uncertain. A real model replaces that classifier only after it is trained on our photos and someone has measured how it behaves. The `models` folder is empty so that an accuracy number cannot be invented by pointing at a file.

## How one button press crosses the stack

This is the path of "Open valve" on Zone 1.

1. The button is HTML.
2. JavaScript notices the click and sends an HTTP request to Flask.
3. Flask, in Python, calls valve safety.
4. If emergency stop is latched, Python refuses and the page shows the reason. No valve opens.
5. If the command is allowed, the simulator starts raising that zone's moisture on the accelerated clock. The other zones keep drying.
6. SQL stores the opening event. The litres column stays empty.
7. JavaScript asks for a new picture and the map shows the valve open.
8. If nobody closes it, Python closes it when the real-time limit is reached, and SQL records why.

Every language in the current stack appears in that path. C++, MQTT, OpenCV, and TensorFlow Lite do not, because they are not part of this path yet.

## What to learn, in order

1. Read Python in `backend/sensors/health.py` and `backend/irrigation/safety.py`. Be able to explain the two-sensor rule and the valve limit in your own words.
2. Read `data/field.json` and change a number only when you know which sentence on the page it affects. Restart after a change.
3. Read the HTML of the page and the matching CSS, so you can adjust wording and layout without breaking the buttons.
4. Read the JavaScript that fetches `/api/field`, so you can explain that the browser displays and Python decides.
5. Learn the five SQL tables at the level of "what each one stores," using `docs/DATA_CONTRACTS.md`.
6. Leave C++, MQTT setup, OpenCV, and any model until the matching phase starts.

## What is installed today

On the development PC:

- Windows
- Python 3.12
- Flask 3.1.3, listed in `requirements.txt`
- SQLite, included with Python
- a web browser

Not installed, and not required for the current phase:

- Mosquitto or any other MQTT broker
- OpenCV
- TensorFlow or TensorFlow Lite
- the Arduino IDE, for the purpose of this software build
- a Raspberry Pi image

## One sentence you can memorise

Kshetra's brain is Python, its memory is SQLite, its page is HTML, CSS, and JavaScript, and the circuit boards will later speak C++ over MQTT and HTTP when the hardware is actually on the bench.
