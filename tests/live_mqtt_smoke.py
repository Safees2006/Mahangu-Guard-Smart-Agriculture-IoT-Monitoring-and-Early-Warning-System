"""Explicit real-broker synthetic smoke test; never represents a Wokwi test."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from mqtt_bridge import BrokerSettings, MQTTBridge
from mqtt_demo import publish_samples
from werkzeug.serving import make_server


def main():
    if "--public-demo" not in sys.argv:
        raise SystemExit("This sends synthetic test readings to a public broker. Explicit --public-demo required.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    evidence = ROOT / "evidence" / "05_testing" / "mqtt"
    evidence.mkdir(parents=True, exist_ok=True)
    (ROOT / "instance").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "instance", ignore_cleanup_errors=True) as work:
        database = str(Path(work) / "mqtt-smoke.sqlite3")
        token = secrets.token_urlsafe(32)
        settings = BrokerSettings("broker.hivemq.com", 1883, "mahangu-guard/demo/verification-" + secrets.token_hex(12) + "/readings", public_demo=True)
        app = create_app({"DATABASE": database, "DEVICE_TOKEN": token, "MQTT_MODE": True})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        bridge = MQTTBridge(settings, url, token)
        started = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
        try:
            bridge.start()
            if not bridge.subscribed.wait(20):
                raise TimeoutError("Public broker subscription not acknowledged within 20 seconds.")
            payloads = publish_samples(settings, "dry", 1)
            if not bridge.delivered.wait(15):
                raise TimeoutError("Published MQTT sample was not accepted by the API within 15 seconds.")
            with urlopen(url + "/api/overview", timeout=5) as response:
                overview = json.load(response)
            with closing(sqlite3.connect(database)) as connection:
                connection.row_factory = sqlite3.Row
                row = dict(connection.execute("SELECT * FROM readings WHERE id=?", (bridge.last_result["reading"]["id"],)).fetchone())
            assert row["source"] == "mqtt_demo"
            assert row["moisture"] == 18
            assert row["timestamp"] == overview["latest"]["timestamp"] == payloads[0]["timestamp"]
            assert row["id"] == overview["latest"]["id"]
            trace = {"run_at": started, "status": "passed", "scope": "Python synthetic publisher -> real public MQTT broker -> Python subscriber -> authenticated loopback HTTP -> SQLite -> overview API. Wokwi firmware not run.", "broker": settings.host, "port": settings.port, "topic": settings.topic, "request_body": payloads[0], "accepted_api_response": bridge.last_result, "database_row": row, "overview": overview}
            (evidence / "P09_mqtt_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
            print("PASS: real MQTT broker -> bridge -> authenticated HTTP -> SQLite -> overview API")
            if "--browser" in sys.argv:
                # The browser fixture checks 18% moisture and two warnings; add heat through MQTT too.
                payload = dict(payloads[0])
                payload.update(timestamp=datetime.now(timezone.utc).isoformat(), temperature=42)
                from mqtt_bridge import new_client
                publisher = new_client(settings, "mahangu-evidence-")
                publisher.connect(settings.host, settings.port, 30)
                publisher.loop_start()
                try:
                    info = publisher.publish(settings.topic, json.dumps(payload), qos=1, retain=False)
                    info.wait_for_publish(timeout=10)
                    bridge.delivered.clear()
                    # Wait for this specific timestamp, not just the first accepted sample.
                    for _ in range(100):
                        if bridge.last_result["reading"]["timestamp"] == payload["timestamp"]:
                            break
                        threading.Event().wait(0.1)
                    else:
                        raise TimeoutError("Second MQTT sample did not reach the backend.")
                    with urlopen(url + "/api/overview", timeout=5) as response:
                        screenshot_overview = json.load(response)
                    with closing(sqlite3.connect(database)) as connection:
                        connection.row_factory = sqlite3.Row
                        screenshot_row = dict(connection.execute("SELECT * FROM readings WHERE id=?", (screenshot_overview["latest"]["id"],)).fetchone())
                    assert screenshot_row["timestamp"] == payload["timestamp"]
                    assert screenshot_row["temperature"] == screenshot_overview["latest"]["temperature"] == 42
                    trace["screenshot_sample"] = {"published_body": payload, "database_row": screenshot_row, "accepted_api_response": bridge.last_result, "overview": screenshot_overview}
                    (evidence / "P09_mqtt_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
                finally:
                    publisher.disconnect()
                    publisher.loop_stop()
                result = subprocess.run(["node", str(ROOT / "tests" / "browser_check.mjs"), url, str(Path(work) / "browser"), str(evidence), "P09_mqtt_demo"], capture_output=True, text=True, timeout=60)
                (evidence / "browser_checks.txt").write_text("MQTT evidence browser run: " + started + "\n" + result.stdout + result.stderr, encoding="utf-8")
                print(result.stdout + result.stderr)
                if result.returncode:
                    raise RuntimeError("Browser verification failed.")
        except Exception as exc:
            (evidence / "last_failure.json").write_text(json.dumps({"run_at": started, "status": "failed", "broker": settings.host, "port": settings.port, "reason": str(exc)}, indent=2), encoding="utf-8")
            raise
        finally:
            bridge.stop()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
