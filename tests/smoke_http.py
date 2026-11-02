"""Real local HTTP + SQLite trace and optional installed-Edge checks."""
from datetime import datetime, timedelta, timezone
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
from urllib.request import urlopen

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from feeder import sample, send


def main():
    evidence = ROOT / "evidence" / "05_testing"
    evidence.mkdir(parents=True, exist_ok=True)
    (ROOT / "instance").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "instance", ignore_cleanup_errors=True) as work:
        database = str(Path(work) / "smoke.sqlite3")
        token = secrets.token_urlsafe(32)
        app = create_app({"DATABASE": database, "DEVICE_TOKEN": token})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            payload = sample("dry")
            payload["temperature"] = 42
            result = send(url, token, payload)
            with urlopen(url + "/api/overview", timeout=5) as response:
                overview = json.load(response)
            with closing(sqlite3.connect(database)) as connection:
                connection.row_factory = sqlite3.Row
                row = dict(connection.execute("SELECT * FROM readings WHERE id=?", (result["reading"]["id"],)).fetchone())
            assert row["timestamp"] == result["reading"]["timestamp"] == overview["latest"]["timestamp"]
            assert row["id"] == overview["latest"]["id"]
            assert row["moisture"] == overview["latest"]["moisture"] == payload["moisture"]
            trace = {"run_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(), "source": "local_demo", "scope": "Real loopback HTTP -> Flask -> temporary SQLite -> overview API. Browser screenshot uses the same sample. Not a Wokwi or physical sensor test.", "request_body": payload, "http_response_body": result, "database_row": row, "overview": overview}
            (evidence / "P09_local_http_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
            print("Real HTTP -> SQLite -> overview identity check: PASS")
            if "--browser" in sys.argv:
                browser = subprocess.run(["node", str(ROOT / "tests" / "browser_check.mjs"), url, str(Path(work) / "edge-profile"), str(evidence)], capture_output=True, text=True, timeout=90)
                log = "Actual browser run: " + trace["run_at"] + "\n" + browser.stdout + browser.stderr
                (evidence / "browser_checks.txt").write_text(log, encoding="utf-8")
                print(log)
                if browser.returncode:
                    raise RuntimeError("Browser checks failed; see evidence log.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
