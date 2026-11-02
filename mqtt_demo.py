"""Publish synthetic MQTT data to test the subscriber; not a Wokwi device test."""
import argparse
import json
import threading
import time

from feeder import SCENARIOS, sample
from mqtt_bridge import load_settings, new_client


def publish_samples(settings, scenario="normal", count=1, interval=5):
    connected = threading.Event()
    rejected = threading.Event()
    client = new_client(settings, "mahangu-test-")

    def on_connect(client, userdata, flags, reason_code, properties):
        (connected if reason_code == 0 else rejected).set()

    client.on_connect = on_connect
    client.connect_async(settings.host, settings.port, keepalive=30)
    client.loop_start()
    try:
        deadline = time.monotonic() + 15
        while not connected.wait(0.1):
            if rejected.is_set() or time.monotonic() >= deadline:
                raise TimeoutError("MQTT connection was not accepted within 15 seconds.")
        payloads = []
        for tick in range(count):
            payload = sample(scenario, tick, settings.device_id)
            payload["source"] = "mqtt_demo"
            info = client.publish(settings.topic, json.dumps(payload), qos=1, retain=False)
            info.wait_for_publish(timeout=10)
            if not info.is_published():
                raise TimeoutError("Broker did not acknowledge the test publish.")
            payloads.append(payload)
            print(f"MQTT synthetic publish acknowledged: {payload['timestamp']} ({scenario})", flush=True)
            if tick < count - 1:
                time.sleep(interval)
        return payloads
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-demo", action="store_true")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    if not 1 <= args.count <= 100 or args.interval < 1:
        parser.error("count must be 1–100 and interval at least 1 second.")
    try:
        publish_samples(load_settings(args.public_demo), args.scenario, args.count, args.interval)
    except (ValueError, TimeoutError) as exc:
        parser.exit(1, str(exc) + "\n")
