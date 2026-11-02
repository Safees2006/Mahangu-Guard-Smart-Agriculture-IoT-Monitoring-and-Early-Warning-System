"""Mahangu Guard: local, educational IoT monitoring application."""
import argparse
import csv
import hmac
import io
import math
import os
from pathlib import Path
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

ROOT = Path(__file__).resolve().parent
PROJECT_NAME = "Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System"
FIELDS = {
    "moisture": (0, 100), "temperature": (-40, 80), "ph": (0, 14),
    "light": (0, 100), "alkalinity": (0, 1000),
}
SOURCES = {"local_demo", "mqtt_demo", "wokwi_simulation", "physical_device"}
DEMO_RULES = {"dry_below": 30, "wet_above": 85, "hot_above": 38,
              "ph_below": 5.5, "ph_above": 7.5, "alkalinity_above": 200}


def utcnow():
    return datetime.now(timezone.utc)


def alerts_for(reading):
    """Demonstration thresholds only; return every concurrent warning."""
    alerts = []
    rules = [
        (reading["moisture"] < 30, "dry", "Dry soil", "Inspect the plot and check the moisture reading."),
        (reading["moisture"] > 85, "wet", "Waterlogging risk", "Inspect drainage and verify the soil condition."),
        (reading["temperature"] > 38, "heat", "High temperature", "Check field conditions and confirm the temperature."),
        (reading["ph"] < 5.5 or reading["ph"] > 7.5, "ph", "pH outside demo range", "Verify with a calibrated probe before taking action."),
        (reading["alkalinity"] > 200, "alkalinity", "High demo alkalinity", "Verify the measurement and consult an agronomist."),
    ]
    for active, code, title, action in rules:
        if active:
            alerts.append({"code": code, "title": title, "action": action})
    return alerts


def validate_payload(data, device_id):
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    required = {"device_id", "timestamp", "source", *FIELDS}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError("Missing fields: " + ", ".join(missing))
    if set(data) - required:
        raise ValueError("Unexpected fields: " + ", ".join(sorted(set(data) - required)))
    if data["device_id"] != device_id:
        raise ValueError("Unregistered device_id.")
    if not isinstance(data["source"], str) or data["source"] not in SOURCES:
        raise ValueError("Unrecognised source.")
    if not isinstance(data["timestamp"], str):
        raise ValueError("timestamp must be an ISO 8601 string with timezone.")
    try:
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO 8601 with timezone.") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must include a timezone.")
    try:
        timestamp = timestamp.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError("timestamp is outside the supported date range.") from exc
    if timestamp.year < 2020 or (timestamp - utcnow()).total_seconds() > 60:
        raise ValueError("timestamp must be since 2020 and no more than 60 seconds in the future.")
    clean = {"device_id": device_id, "timestamp": timestamp.isoformat(), "source": data["source"]}
    for field, (low, high) in FIELDS.items():
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be a finite number from {low} to {high}.")
        try:
            valid = math.isfinite(value) and low <= value <= high
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"{field} must be a finite number from {low} to {high}.")
        clean[field] = float(value)
    return clean


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=str(ROOT / "instance" / "mahangu.sqlite3"),
        DEVICE_TOKEN=os.environ.get("MAHANGU_DEVICE_TOKEN"),
        DEVICE_ID=os.environ.get("MAHANGU_DEVICE_ID", "mahangu-01"),
        MQTT_MODE=False,
        STALE_SECONDS=20, MAX_CONTENT_LENGTH=8192,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    if not app.config["DEVICE_TOKEN"]:
        token_path = ROOT / "instance" / "device-token"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with token_path.open("x", encoding="utf-8") as f:
                f.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass
        app.config["DEVICE_TOKEN"] = token_path.read_text(encoding="utf-8").strip()
    if len(app.config["DEVICE_TOKEN"]) < 24:
        raise ValueError("Device token must contain at least 24 characters.")

    @contextmanager
    def db():
        connection = sqlite3.connect(app.config["DATABASE"], timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with db() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL, timestamp TEXT NOT NULL, received_at TEXT NOT NULL,
            source TEXT NOT NULL, moisture REAL NOT NULL, temperature REAL NOT NULL,
            ph REAL NOT NULL, light REAL NOT NULL, alkalinity REAL NOT NULL,
            UNIQUE(device_id, timestamp))""")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_device_time ON readings(device_id, timestamp DESC)")

    def serialise(row):
        reading = dict(row)
        reading["alerts"] = alerts_for(reading)
        return reading

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        return response

    @app.get("/")
    def index():
        return render_template("index.html", device_id=app.config["DEVICE_ID"], mqtt_mode=app.config["MQTT_MODE"], project_name=PROJECT_NAME)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", mode="educational_prototype", server_time=utcnow().isoformat())

    @app.post("/api/readings")
    def ingest():
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied.encode(), ("Bearer " + app.config["DEVICE_TOKEN"]).encode()):
            return jsonify(error="Device authentication required."), 401
        if not request.is_json:
            return jsonify(error="Content-Type must be application/json."), 415
        try:
            reading = validate_payload(request.get_json(), app.config["DEVICE_ID"])
        except (ValueError, BadRequest) as exc:
            message = str(exc) if isinstance(exc, ValueError) else "Malformed JSON."
            return jsonify(error=message), 400
        received_at = utcnow().isoformat()
        try:
            with db() as connection:
                cursor = connection.execute(
                    """INSERT INTO readings(device_id, timestamp, received_at, source,
                    moisture, temperature, ph, light, alkalinity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (reading["device_id"], reading["timestamp"], received_at, reading["source"],
                     *(reading[field] for field in FIELDS)),
                )
                reading["id"] = cursor.lastrowid
        except sqlite3.IntegrityError:
            return jsonify(error="Duplicate device timestamp; reading already stored."), 409
        reading.update(received_at=received_at, alerts=alerts_for(reading))
        return jsonify(reading=reading), 201

    @app.get("/api/overview")
    def overview():
        now = utcnow()
        with db() as connection:
            row = connection.execute("SELECT * FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT 1", (app.config["DEVICE_ID"],)).fetchone()
            count = connection.execute("SELECT COUNT(*) FROM readings WHERE device_id=?", (app.config["DEVICE_ID"],)).fetchone()[0]
        latest = serialise(row) if row else None
        age = max(0, (now - datetime.fromisoformat(row["timestamp"])).total_seconds()) if row else None
        stale = age is None or age > app.config["STALE_SECONDS"]
        return jsonify(
            latest=latest, count=count, server_time=now.isoformat(), age_seconds=age,
            stale_seconds=app.config["STALE_SECONDS"],
            connection="waiting" if not row else "stale" if stale else "current",
            thresholds=DEMO_RULES,
            weather={"status": "not_configured", "message": "No live forecast connected. Check a trusted local forecast before field decisions."},
        )

    @app.get("/api/readings")
    def history():
        try:
            limit = int(request.args.get("limit", "60"))
            if not 1 <= limit <= 500:
                raise ValueError
        except ValueError:
            return jsonify(error="limit must be an integer between 1 and 500."), 400
        with db() as connection:
            rows = connection.execute("SELECT * FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT ?", (app.config["DEVICE_ID"], limit)).fetchall()
        return jsonify(readings=[serialise(row) for row in reversed(rows)])

    @app.get("/api/export.csv")
    def export():
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        columns = ["id", "device_id", "timestamp", "received_at", "source", *FIELDS]
        writer.writerow(columns)
        with db() as connection:
            for row in connection.execute("SELECT * FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT 10000", (app.config["DEVICE_ID"],)):
                # Defend spreadsheet exports against configurable device identifiers.
                values = [row[c] for c in columns]
                writer.writerow(["'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v for v in values])
        return Response(stream.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=mahangu-readings.csv"})

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(error="Payload exceeds 8 KiB."), 413

    @app.errorhandler(UnsupportedMediaType)
    def unsupported(_error):
        return jsonify(error="Expected application/json."), 415

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Send synthetic readings every five seconds through the authenticated HTTP API.")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    application = create_app()
    if args.demo:
        from feeder import run_demo
        threading.Thread(target=run_demo, kwargs={"base_url": f"http://127.0.0.1:{args.port}", "token": application.config["DEVICE_TOKEN"], "device_id": application.config["DEVICE_ID"]}, daemon=True).start()
    print(f"Mahangu Guard: http://127.0.0.1:{args.port} | Ctrl+C to stop", flush=True)
    application.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
