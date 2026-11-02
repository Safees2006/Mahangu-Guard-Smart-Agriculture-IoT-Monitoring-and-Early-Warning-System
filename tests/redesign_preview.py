"""Browser QA fixture for the redesigned UI. Every preview sample is synthetic."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from feeder import sample, send
from werkzeug.serving import make_server


def main():
    evidence = ROOT / "evidence" / "07_iterations" / "dashboard_redesign"
    evidence.mkdir(parents=True, exist_ok=True)
    work = ROOT / "instance" / ("ui-preview-" + secrets.token_hex(5))
    work.mkdir()
    token = secrets.token_urlsafe(32)
    app = create_app({"DATABASE": str(work / "preview.sqlite3"), "DEVICE_TOKEN": token, "MQTT_MODE": True})
    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        anchor = datetime.now(timezone.utc)
        levels = [59, 52, 44, 57, 68, 62, 49, 54, 41, 46, 59, 71, 65, 48, 56]
        accepted = []
        for index, moisture in enumerate(levels):
            payload = sample()
            payload.update(timestamp=(anchor - timedelta(seconds=(16-index)*5)).isoformat(), moisture=moisture)
            accepted.append(send(url, token, payload)["reading"])
        payload = sample("dry")
        payload["temperature"] = 42
        accepted.append(send(url, token, payload)["reading"])
        with urlopen(url + "/api/overview", timeout=5) as response:
            overview = json.load(response)
        (evidence / "synthetic_fixture.json").write_text(json.dumps({"captured_at":datetime.now(timezone(timedelta(hours=5,minutes=30))).isoformat(),"scope":"UI test fixture: 16 deliberately generated local_demo samples sent through actual HTTP validation/storage. Not Wokwi or field measurements.","readings":accepted,"overview":overview},indent=2),encoding="utf-8")
        result = subprocess.run(["node",str(ROOT/"tests"/"browser_check.mjs"),url,str(work/"edge"),str(evidence),"redesigned"],capture_output=True,text=True,timeout=90)
        (evidence / "browser_checks.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
        print(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError("Redesign browser checks failed.")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
