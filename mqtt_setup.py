"""Create matching, non-secret MQTT demo topic settings for Wokwi and Python."""
import json
import os
from pathlib import Path
import re
import secrets

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "instance" / "mqtt-demo.json"


def prepare():
    device_id = os.environ.get("MAHANGU_DEVICE_ID", "mahangu-01")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", device_id):
        raise ValueError("MQTT demo device ID must use 1–64 letters, numbers, underscores or hyphens.")
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SETTINGS_PATH.exists():
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if settings["device_id"] != device_id:
            raise ValueError("Existing MQTT demo uses another device ID. Set MAHANGU_DEVICE_ID to match it.")
    else:
        settings = {"host": "broker.hivemq.com", "port": 1883,
                    "topic": f"mahangu-guard/demo/{secrets.token_hex(12)}/{device_id}/readings", "device_id": device_id}
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    config_path = ROOT / "wokwi" / "mqtt" / "config.h"
    if not config_path.exists():
        template = (config_path.parent / "config.h.example").read_text(encoding="utf-8")
        template = template.replace('"REPLACE_WITH_TOPIC_FROM_MQTT_SETUP"', json.dumps(settings["topic"]))
        template = template.replace('#define DEVICE_ID "mahangu-01"', '#define DEVICE_ID ' + json.dumps(device_id))
        config_path.write_text(template, encoding="utf-8")
    return settings, config_path


if __name__ == "__main__":
    settings, config_path = prepare()
    print("MQTT demo ready (anonymous public broker; synthetic data only).")
    print(f"Broker: {settings['host']}:{settings['port']}")
    print(f"Topic: {settings['topic']}")
    print(f"Copy this generated file to the Wokwi config.h tab: {config_path}")
    print("Existing settings and config.h are preserved on rerun.")
