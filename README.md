# Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System

A local Unit 45 IoT project for the fictional Mushimba-Shikongo Grain client in Kavango East, Namibia. Flask receives authenticated JSON readings, validates and stores them in SQLite, and serves a responsive monitoring dashboard.

**Wokwi simulation:** [Open the saved Mahangu Guard project](https://wokwi.com/projects/479554649720488961).

**Dashboard preview:** [Desktop](evidence/07_iterations/dashboard_redesign/redesigned_dashboard_desktop.png) · [Mobile](evidence/07_iterations/dashboard_redesign/redesigned_dashboard_mobile.png). These screenshots use a clearly labelled synthetic UI test fixture.

## Start on this computer

Requires Python 3.10 or later. For a fresh computer, follow the clean-environment commands below. If the dependencies are already installed, run from this directory:

```powershell
python app.py --demo
```

Open **http://127.0.0.1:5000**. The demo sends a synthetic reading through the HTTP API every five seconds. Leave the terminal running; Ctrl+C stops the application and its demo thread. The first reading arrives about one second after startup. The dashboard polls every four seconds.

Alternatively, run `powershell -ExecutionPolicy Bypass -File .\start.ps1`. Add `-NoDemo` to start with no automatic feeder, or `-Port 5050` to use a different port.

For a clean environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --demo
```

No Node packages, cloud account, weather key or paid service is needed for the local demo. CSS, JavaScript and charts are served locally; there are no external font or chart requests.

## Try a warning

Start the server **without** its continuous demo:

```powershell
python app.py
```

In a second terminal:

```powershell
python feeder.py --scenario dry --count 1
python feeder.py --scenario heat --count 1
python feeder.py --scenario ph --count 1
python feeder.py --scenario wet --count 1
python feeder.py --scenario alkalinity --count 1
python feeder.py --scenario normal --count 1
```

Wait up to four seconds for each dashboard update. With no new samples, the latest sample becomes stale after 20 seconds. Stopping the backend produces a disconnected state; historical values remain visible in an already-open browser. Each scenario uses `source: local_demo` and cannot establish physical sensor accuracy.

## What is included

- Responsive overview, recent trends with a measurement selector, warning guidance, last-update age and history.
- Required moisture, temperature, light, pH and **separate alkalinity** values. Light is a relative percentage, not lux; alkalinity uses synthetic mg/L as CaCO₃, not soil salinity.
- Registered device ID and bearer authentication for every ingestion request; token created locally and omitted from browser code, logs and version control.
- Finite-number, type, range, timestamp, device, source and payload-size validation.
- Persistent SQLite storage, duplicate rejection, sample-time ordering and CSV export (up to the most recent 10,000 rows).
- Repeatable automated backend tests, Wokwi circuit/firmware starter, requirements, architecture, evidence folders and feedback template.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Service status |
| `POST /api/readings` | Validate and store a sample; requires `Authorization: Bearer <device token>` |
| `GET /api/overview` | Latest sample, warnings, count, sample freshness and weather availability |
| `GET /api/readings?limit=60` | Chronological history; limit 1–500 |
| `GET /api/export.csv` | Download recent stored samples |

Example body (use a current timestamp when transmitting):

```json
{
  "device_id": "mahangu-01",
  "timestamp": "2026-11-02T10:00:00+05:30",
  "source": "local_demo",
  "moisture": 58,
  "temperature": 30,
  "ph": 6.4,
  "light": 76,
  "alkalinity": 110
}
```

The timestamp requires a timezone, cannot predate 2020, and cannot exceed server time by more than 60 seconds. Delayed samples are retained but do not replace more recent sample-time readings. Duplicate device/timestamp pairs return 409; invalid input returns 400; missing/incorrect authentication returns 401; wrong content type returns 415; bodies above 8 KiB return 413.

The generated token is stored in `instance/device-token`; the database is `instance/mahangu.sqlite3`. Keep the entire `instance/` directory private. For your own token, set `MAHANGU_DEVICE_TOKEN` (at least 24 characters) in both the server and feeder environments. Set `MAHANGU_DEVICE_ID` consistently to change the registered device. Source labels are device declarations, not cryptographic attestations of physical hardware.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
python tests/smoke_http.py --browser
```

The tests use an isolated temporary database. T01–T08 cover the planned software behaviours, including stale metadata and restart persistence. The full suite now includes MQTT boundary, retry and configuration checks. The optional HTTP/browser smoke script uses an installed Microsoft Edge at its standard Windows path and Node 24, a separate temporary database and a disposable browser profile; it saves a matching HTTP/database trace and real desktop/mobile screenshots. Browser QA verifies chart selection, concurrent warnings, provenance, viewport overflow, stale state using an advanced browser clock, and disconnection using browser offline emulation. It does not replace Wokwi delivery evidence, participant experiments or field calibration. Actual output is recorded under `evidence/05_testing/`; see `VERIFICATION.md` there and `mqtt/README.md` for the later MQTT run. Windows sandbox restrictions required an elevated execution context for the test temporary directories and headless browser in this session.

To explicitly repeat the real public-broker synthetic MQTT check (publishes two test readings if browser mode is used):

```powershell
.\.venv\Scripts\python.exe tests/live_mqtt_smoke.py --public-demo --browser
```

## ESP32 / Wokwi

**MQTT is now available:** use [the MQTT setup guide](wokwi/mqtt/README.md) or [Tamil/Tanglish steps](docs/MQTT_SETUP_TAMIL.md). The public-broker path needs no Wokwi private gateway. The Python publisher/subscriber/backend path was verified over a real public broker. A later user-supplied Wokwi Serial run confirmed startup, time synchronization and three MQTT samples that matched SQLite IDs 22–24; see [the Wokwi evidence](evidence/04_development/wokwi_479554649720488961/README.md).

```powershell
.\.venv\Scripts\python.exe mqtt_setup.py
.\.venv\Scripts\python.exe mqtt_bridge.py --public-demo --serve
```

The separate MQTT dashboard is **http://127.0.0.1:5050**, with no automatic HTTP demo feeder. Use all four files from `wokwi/mqtt/` in Wokwi, including the generated `config.h`. The shared public broker is for untrusted synthetic readings only. The local API token is never sent to the broker.

The original **direct HTTP** version remains in [wokwi/README.md](wokwi/README.md). It has not been compiled or run in Wokwi here. A cloud simulator cannot access your laptop through its own `localhost`; that direct path needs a private gateway or separately configured reachable service. MQTT instead uses an internet-reachable broker and a laptop subscriber.

## Project boundaries

This first stage follows the three **named** report drafts and supplied PDF. The original reports in Downloads are unchanged. Their embedded instructions are planning context; they do not establish completed tests, real feedback or implemented features. The referenced `Codex_Project` and `CODEX_TASK.md` were not among the supplied files, so this starter was built from the supplied plan.

All alert bands are **demonstration values**, pending agricultural review. A live forecast is **not connected**, and the UI says so. Alkalinity and pH are test-generated proxies. There is no automated irrigation, crop-yield prediction or claim of field deployment. This is a local Python application; it has not been published to cloud hosting. The read-only dashboard and export are local and have no user login; add access controls and a production server before remote use.

Next work: verify Wokwi transport, capture screenshots using the evidence guide, obtain consented participant feedback, make documented improvements, and complete the evaluation using actual results.

## Working together

Each contributor should clone the repository, create their own Python environment, install `requirements.txt`, and work on a separate branch. Open a pull request for review before merging into `main`.

Runtime data and credentials are deliberately excluded from Git: `instance/`, `.venv/`, `.env` and private `config.h` files. Each computer should run `mqtt_setup.py` to generate its local demo configuration. Use the matching generated `wokwi/mqtt/config.h` in Wokwi. A shared Wokwi project and a newly generated laptop topic must match before telemetry can flow; do not assume a new clone shares the original laptop's local settings.
