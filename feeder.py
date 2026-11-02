"""Local synthetic input; does not represent a Wokwi or physical sensor test."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCENARIOS = {
    "normal": {"moisture": 58, "temperature": 30, "ph": 6.4, "light": 76, "alkalinity": 110},
    "dry": {"moisture": 18, "temperature": 32, "ph": 6.4, "light": 82, "alkalinity": 110},
    "heat": {"moisture": 52, "temperature": 42, "ph": 6.4, "light": 90, "alkalinity": 110},
    "ph": {"moisture": 55, "temperature": 30, "ph": 8.2, "light": 72, "alkalinity": 110},
    "wet": {"moisture": 94, "temperature": 28, "ph": 6.4, "light": 40, "alkalinity": 110},
    "alkalinity": {"moisture": 55, "temperature": 30, "ph": 6.4, "light": 72, "alkalinity": 280},
}


def sample(scenario="normal", tick=0, device_id="mahangu-01"):
    values = dict(SCENARIOS[scenario])
    values["moisture"] = round(values["moisture"] + math.sin(tick / 3) * 2, 1)
    values["temperature"] = round(values["temperature"] + math.sin(tick / 4) * 0.8, 1)
    return {"device_id": device_id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "local_demo", **values}


def send(base_url, token, payload):
    request = Request(base_url.rstrip("/") + "/api/readings", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + token}, method="POST")
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def run_demo(base_url, token, device_id="mahangu-01", scenario="normal", interval=5, count=None):
    tick = 0
    # Delay startup so app.py --demo can bind the HTTP listener.
    time.sleep(1)
    while count is None or tick < count:
        try:
            result = send(base_url, token, sample(scenario, tick, device_id))
            print(f"[local demo] Stored reading {result['reading']['id']} ({scenario})", flush=True)
        except HTTPError as exc:
            print(f"[local demo] API returned HTTP {exc.code}; check configuration.", flush=True)
        except (URLError, TimeoutError, OSError):
            print("[local demo] Backend unreachable; will retry.", flush=True)
        tick += 1
        if count is None or tick < count:
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--count", type=int)
    args = parser.parse_args()
    if args.interval < 0.1 or (args.count is not None and args.count < 1):
        parser.error("interval must be >= 0.1; count must be >= 1")
    token = os.environ.get("MAHANGU_DEVICE_TOKEN")
    if not token:
        token_file = Path(__file__).resolve().parent / "instance" / "device-token"
        if not token_file.exists():
            parser.error("Start app.py first to create the local device token.")
        token = token_file.read_text(encoding="utf-8").strip()
    try:
        run_demo(args.url, token, os.environ.get("MAHANGU_DEVICE_ID", "mahangu-01"), args.scenario, args.interval, args.count)
    except KeyboardInterrupt:
        print("Demo feeder stopped.")
