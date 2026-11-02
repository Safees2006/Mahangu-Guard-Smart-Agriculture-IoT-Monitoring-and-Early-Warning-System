"""MQTT subscriber -> authenticated loopback Flask API. No API token enters MQTT."""
import argparse
from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import queue
import secrets
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

import paho.mqtt.client as mqtt

from app import ROOT, create_app, validate_payload
from feeder import send
from mqtt_setup import SETTINGS_PATH

LOG = logging.getLogger("mahangu.mqtt")


@dataclass(frozen=True)
class BrokerSettings:
    host: str
    port: int
    topic: str
    device_id: str = "mahangu-01"
    public_demo: bool = False
    tls: bool = False
    username: str = ""
    password: str = field(default="", repr=False)
    ca_file: str | None = None
    transport: str = "tcp"

    def validate(self):
        if not self.host or not 1 <= self.port <= 65535:
            raise ValueError("Valid MQTT host and port required.")
        if not self.topic or any(char in self.topic for char in ("#", "+", "\x00")) or len(self.topic.encode()) > 300:
            raise ValueError("Use a single exact MQTT topic, up to 300 bytes, without wildcards.")
        if self.transport not in {"tcp", "websockets"}:
            raise ValueError("MQTT_TRANSPORT must be tcp or websockets.")
        if self.public_demo and (self.username or self.password):
            raise ValueError("Public demo must not contain credentials; use private TLS mode for credentials.")
        if not self.public_demo and not (self.tls and self.username and self.password):
            raise ValueError("Private mode requires TLS, MQTT_USERNAME and MQTT_PASSWORD; or explicitly use --public-demo for synthetic data.")


def load_settings(public_demo=False):
    defaults = {}
    if public_demo and SETTINGS_PATH.exists():
        defaults = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    settings = BrokerSettings(
        host=os.environ.get("MQTT_HOST", defaults.get("host", "")),
        port=int(os.environ.get("MQTT_PORT", str(defaults.get("port", 8883)))),
        topic=os.environ.get("MQTT_TOPIC", defaults.get("topic", "")),
        device_id=os.environ.get("MAHANGU_DEVICE_ID", defaults.get("device_id", "mahangu-01")),
        public_demo=public_demo, tls=os.environ.get("MQTT_TLS", "0" if public_demo else "1") == "1",
        username=os.environ.get("MQTT_USERNAME", ""), password=os.environ.get("MQTT_PASSWORD", ""),
        ca_file=os.environ.get("MQTT_CA_FILE") or None,
        transport=os.environ.get("MQTT_TRANSPORT", "tcp"),
    )
    settings.validate()
    return settings


def new_client(settings, prefix):
    settings.validate()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=prefix + secrets.token_hex(6), protocol=mqtt.MQTTv311, transport=settings.transport)
    client.connect_timeout = 10
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    if settings.transport == "websockets":
        client.ws_set_options(path="/mqtt")
    if settings.tls:
        client.tls_set(ca_certs=settings.ca_file)  # Certificate and hostname verification stay enabled.
    if settings.username:
        client.username_pw_set(settings.username, settings.password)
    return client


class MQTTBridge:
    def __init__(self, settings, base_url, token, sender=send):
        settings.validate()
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("Bridge HTTP destination must be the local loopback API root.")
        self.settings, self.base_url, self.token = settings, base_url, token
        self.sender = sender
        self.messages = queue.Queue(maxsize=100)
        self.stopping = threading.Event()
        self.subscribed = threading.Event()
        self.delivered = threading.Event()
        self.client = new_client(settings, "mahangu-bridge-")
        self.client.on_connect = self.on_connect
        self.client.on_connect_fail = self.on_connect_fail
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.worker = None
        self.accepted = 0
        self.rejected = 0
        self.last_result = None

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            LOG.warning("Broker rejected connection; check MQTT settings.")
            return
        result, _mid = client.subscribe(self.settings.topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            LOG.warning("Could not request MQTT subscription.")

    def on_connect_fail(self, client, userdata):
        self.subscribed.clear()
        LOG.warning("MQTT connection failed; retrying with backoff.")

    def on_subscribe(self, client, userdata, mid, reason_codes, properties):
        if not reason_codes or any(code.is_failure for code in reason_codes):
            LOG.warning("Broker rejected MQTT subscription.")
            return
        self.subscribed.set()
        LOG.info("MQTT subscribed; waiting for new readings.")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.subscribed.clear()
        if not self.stopping.is_set():
            LOG.warning("MQTT disconnected; reconnecting. Dashboard sample age continues to increase.")

    def decode_message(self, message):
        if message.topic != self.settings.topic:
            raise ValueError("Unexpected topic.")
        if message.retain:
            raise ValueError("Retained samples are not accepted as fresh telemetry.")
        if len(message.payload) > 8192:
            raise ValueError("Payload exceeds 8 KiB.")
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError) as exc:
            raise ValueError("Invalid JSON payload.") from exc
        clean = validate_payload(payload, self.settings.device_id)
        if self.settings.public_demo and clean["source"] not in {"local_demo", "mqtt_demo", "wokwi_simulation"}:
            raise ValueError("Public demo accepts synthetic sources only.")
        return clean

    def on_message(self, client, userdata, message):
        try:
            payload = self.decode_message(message)
            self.messages.put_nowait(payload)
        except (ValueError, queue.Full):
            self.rejected += 1
            LOG.warning("MQTT message rejected: invalid, retained, wrong source, or queue full.")

    def forward(self, payload):
        for attempt in range(3):
            try:
                result = self.sender(self.base_url, self.token, payload)
                self.accepted += 1
                self.last_result = result
                self.delivered.set()
                reading = result["reading"]
                LOG.info("MQTT -> API stored id=%s timestamp=%s source=%s", reading["id"], reading["timestamp"], reading["source"])
                return "stored"
            except HTTPError as exc:
                exc.close()
                if exc.code == 409:
                    LOG.info("Duplicate sample already stored; skipped.")
                    return "duplicate"
                self.rejected += 1
                LOG.warning("API rejected MQTT sample (HTTP %s); check device and token configuration.", exc.code)
                return "rejected"
            except (URLError, OSError, TimeoutError):
                if attempt < 2 and not self.stopping.wait(2 ** attempt):
                    continue
                self.rejected += 1
                LOG.warning("Local API unavailable; sample dropped after bounded retries (no disk buffer).")
                return "unavailable"

    def work(self):
        while not self.stopping.is_set():
            try:
                payload = self.messages.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.forward(payload)
            finally:
                self.messages.task_done()

    def start(self):
        self.worker = threading.Thread(target=self.work, daemon=True)
        self.worker.start()
        self.client.connect_async(self.settings.host, self.settings.port, keepalive=30)
        self.client.loop_start()

    def stop(self):
        self.stopping.set()
        self.client.disconnect()
        self.client.loop_stop()
        if self.worker:
            self.worker.join(timeout=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-demo", action="store_true", help="Explicitly allow anonymous synthetic test-broker telemetry.")
    parser.add_argument("--serve", action="store_true", help="Also run an isolated MQTT dashboard, without the local HTTP demo feeder.")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        settings = load_settings(args.public_demo)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc) + " Run mqtt_setup.py for a public demo.")
    token = os.environ.get("MAHANGU_DEVICE_TOKEN")
    server = None
    if args.serve:
        from werkzeug.serving import make_server
        application = create_app({"DATABASE": str(ROOT / "instance" / "mahangu-mqtt.sqlite3"), "DEVICE_ID": settings.device_id, "MQTT_MODE": True})
        token = application.config["DEVICE_TOKEN"]
        server = make_server("127.0.0.1", args.port, application, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        args.url = f"http://127.0.0.1:{args.port}"
        print(f"MQTT dashboard: {args.url} (separate database; no HTTP demo feeder)", flush=True)
    if not token:
        token_path = ROOT / "instance" / "device-token"
        if not token_path.exists():
            parser.error("Start the local backend first, or use --serve.")
        token = token_path.read_text(encoding="utf-8").strip()
    bridge = MQTTBridge(settings, args.url, token)
    if settings.public_demo:
        LOG.info("PUBLIC DEMO: anonymous broker; untrusted synthetic readings only. API token stays on this laptop.")
    try:
        bridge.start()
        while not bridge.stopping.wait(1):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
