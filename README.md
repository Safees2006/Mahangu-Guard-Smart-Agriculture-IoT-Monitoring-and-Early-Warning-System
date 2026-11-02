# Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System

An ESP32/Wokwi monitoring project with a responsive web dashboard. Simulated sensor readings travel through MQTT to a local Flask service, which validates the data, stores it in SQLite and displays readings, history and early warnings.

**Wokwi:** [Open the saved ESP32 simulation](https://wokwi.com/projects/479554649720488961).

## Project structure

```text
app.py                  Flask API, validation, alerts and SQLite storage
mqtt_bridge.py          MQTT subscriber and authenticated local API forwarding
mqtt_setup.py           Generate matching laptop/Wokwi demo settings
mqtt_demo.py            Synthetic MQTT publisher
feeder.py               Synthetic HTTP publisher
start-mqtt.ps1          Windows MQTT startup
start.ps1               Windows local demo startup
templates/              Dashboard HTML
static/                 Dashboard CSS, JavaScript and original SVG assets
wokwi/                  ESP32 circuit, libraries and firmware variants
tests/                  Backend, MQTT and browser checks
docs/                   Architecture, dashboard design and MQTT setup
```

## Install

Requires Python 3.10 or later. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The dashboard uses locally served CSS, JavaScript and SVG charts. No Node build step is required to run it.

## Run Wokwi and the MQTT dashboard

```powershell
.\.venv\Scripts\python.exe mqtt_setup.py
.\.venv\Scripts\python.exe mqtt_bridge.py --public-demo --serve
```

Open **http://127.0.0.1:5050** and keep the terminal running. On Windows, `powershell -ExecutionPolicy Bypass -File .\start-mqtt.ps1` performs setup and startup.

Use the [MQTT firmware instructions](wokwi/mqtt/README.md) or [Tamil/Tanglish guide](docs/MQTT_SETUP_TAMIL.md). Copy `sketch.ino`, `diagram.json`, `libraries.txt` and the locally generated `config.h` from `wokwi/mqtt/` into an ESP32 Arduino project in Wokwi. Start the simulation and confirm both Serial publication and an accepted sample on the dashboard.

If you prefer no `config.h` tab, use the [single-file firmware](wokwi/mqtt_single_file/README.md). Its `MQTT_TOPIC` must match your laptop's `instance/mqtt-demo.json`. A fresh clone generates its own topic; update a shared Wokwi project to match before expecting readings.

The default public demo uses `broker.hivemq.com:1883`. MQTT mode has a separate database, `instance/mahangu-mqtt.sqlite3`, and no automatic HTTP feeder. The local API token stays on the laptop and is never sent to the broker.

To try MQTT warnings without Wokwi, keep the dashboard running and use another terminal:

```powershell
.\.venv\Scripts\python.exe mqtt_demo.py --public-demo --scenario dry
.\.venv\Scripts\python.exe mqtt_demo.py --public-demo --scenario heat
.\.venv\Scripts\python.exe mqtt_demo.py --public-demo --scenario normal
```

These Python-generated readings use the `mqtt_demo` source label. Wokwi uses `wokwi_simulation`.

## Run the local HTTP demo

```powershell
.\.venv\Scripts\python.exe app.py --demo
```

Open **http://127.0.0.1:5000**. The synthetic feeder publishes every five seconds and the browser polls every four seconds. Ctrl+C stops the server.

For manual scenarios, start `app.py` without `--demo`, then run `feeder.py --scenario dry --count 1` in another terminal. Supported scenarios are `normal`, `dry`, `heat`, `ph`, `wet` and `alkalinity`.

## Dashboard features

- Moisture, temperature, pH, relative light and a separate synthetic alkalinity input.
- Desktop sidebar, mobile navigation, sensor cards, condition gauge and original field illustration.
- Configured warning text, sample age, and explicit stale/disconnected states.
- Measurement selector, 10/30/60-sample chart windows, searchable/expanded history and CSV export.
- Validated timestamped input, duplicate rejection and persistent SQLite history.

The gauge counts four configured checks; it is not an agronomic health score. Light is a relative percentage, and alkalinity is a synthetic mg/L-as-CaCO3 proxy. The demonstration thresholds require agricultural review. Live weather, physical calibration and automated irrigation are not implemented.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Service status |
| `POST /api/readings` | Validate and store JSON; requires `Authorization: Bearer <device token>` |
| `GET /api/overview` | Latest sample, warnings, count, age and weather availability |
| `GET /api/readings?limit=60` | Chronological history; limit 1–500 |
| `GET /api/export.csv` | Export up to the most recent 10,000 stored readings |

Required JSON fields: `device_id`, `timestamp`, `source`, `moisture`, `temperature`, `ph`, `light` and `alkalinity`. Use the registered device ID (default `mahangu-01`) and a current ISO 8601 timestamp including a timezone. Values must be finite numbers within the ranges in `app.py`. Duplicate device/timestamp pairs return 409; invalid input returns 400; incorrect authentication returns 401; wrong media type returns 415; bodies above 8 KiB return 413.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
```

Optional smoke checks:

```powershell
.\.venv\Scripts\python.exe tests/smoke_http.py --browser
.\.venv\Scripts\python.exe tests/live_mqtt_smoke.py --public-demo --browser
```

The MQTT smoke check publishes synthetic readings to the public broker. Browser checks require Microsoft Edge at its standard Windows path and Node 24. Generated traces and screenshots remain local in the ignored `evidence/` directory.

## Configuration and deployment

Tokens, `.env` files, generated `config.h`, databases and `.venv` stay outside version control. `MAHANGU_DEVICE_TOKEN` can override the locally generated token; it must have at least 24 characters. Set `MAHANGU_DEVICE_ID` consistently in the service, publishers and firmware to change the device ID.

The public MQTT listener is anonymous and unencrypted. Use synthetic readings only. Source labels are self-reported, and a random topic does not authenticate a publisher. The device has no persistent offline buffer. Private TLS, broker credentials and topic ACL configuration are described in the MQTT guide; private-broker operation has not been live-tested. The local dashboard has no login and uses a development server; remote deployment requires suitable authentication and production hosting.

## Working together

Each contributor should clone the repository, create their own Python environment and work on a separate branch. Open a pull request before merging into `main`. Each computer should run `mqtt_setup.py` and use matching laptop/firmware settings. Grant a teammate repository access through GitHub **Settings → Collaborators**.

This repository contains the dashboard, Wokwi firmware and supporting project source. Assignment reports, PDFs, evidence screenshots and generated archives are excluded.
