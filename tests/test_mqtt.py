"""MQTT message boundary, retry and local API security checks; no network broker."""
from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from feeder import sample
from mqtt_bridge import BrokerSettings, MQTTBridge

TOKEN = "test-only-token-with-at-least-24-characters"


class MQTTTests(unittest.TestCase):
    def setUp(self):
        self.settings = BrokerSettings("test.mosquitto.org", 1883, "mahangu-guard/demo/test-only/device/readings", public_demo=True)
        self.sender = Mock(return_value={"reading": {"id": 1, "timestamp": "test-time", "source": "mqtt_demo"}})
        self.bridge = MQTTBridge(self.settings, "http://127.0.0.1:5000", TOKEN, sender=self.sender)

    def message(self, data=None, **overrides):
        if data is None:
            data = sample()
            data["source"] = "mqtt_demo"
        values = {"topic": self.settings.topic, "payload": json.dumps(data).encode(), "retain": False}
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_valid_message_is_queued_and_forwarded_with_local_token(self):
        message = self.message()
        self.bridge.on_message(None, None, message)
        payload = self.bridge.messages.get_nowait()
        self.assertEqual(payload["source"], "mqtt_demo")
        self.assertEqual(self.bridge.forward(payload), "stored")
        self.sender.assert_called_once_with("http://127.0.0.1:5000", TOKEN, payload)
        self.assertNotIn(TOKEN, message.payload.decode())
        self.assertTrue(self.bridge.delivered.is_set())

    def test_retained_wrong_topic_and_large_messages_are_rejected(self):
        for message in [self.message(retain=True), self.message(topic="somebody-else"), self.message(payload=b"x" * 8193)]:
            with self.subTest(message=message):
                self.bridge.on_message(None, None, message)
        self.assertEqual(self.bridge.rejected, 3)
        self.assertTrue(self.bridge.messages.empty())

    def test_invalid_json_and_non_finite_values_are_rejected(self):
        for raw in [b"{broken", b"\xff", b"[]", b"null"]:
            self.bridge.on_message(None, None, self.message(payload=raw))
        payload = sample()
        payload["moisture"] = float("nan")
        self.bridge.on_message(None, None, self.message(payload))
        self.assertEqual(self.bridge.rejected, 5)
        self.assertTrue(self.bridge.messages.empty())

    def test_public_demo_cannot_accept_claimed_physical_device(self):
        payload = sample()
        payload["source"] = "physical_device"
        self.bridge.on_message(None, None, self.message(payload))
        self.assertEqual(self.bridge.rejected, 1)

    def test_wrong_device_and_extra_secret_fields_are_rejected(self):
        for changes in [{"device_id": "not-registered"}, {"device_token": "do-not-send-secrets"}, {"timestamp": "no-timezone"}]:
            payload = sample()
            payload.update(changes)
            self.bridge.on_message(None, None, self.message(payload))
        self.assertEqual(self.bridge.rejected, 3)

    def test_queue_is_bounded(self):
        for _ in range(100):
            self.bridge.messages.put_nowait(sample())
        self.bridge.on_message(None, None, self.message())
        self.assertEqual(self.bridge.messages.qsize(), 100)
        self.assertEqual(self.bridge.rejected, 1)

    def test_duplicate_and_auth_failure_are_not_retried(self):
        for code, expected in [(409, "duplicate"), (401, "rejected")]:
            with self.subTest(code=code):
                self.sender.reset_mock()
                self.sender.side_effect = HTTPError("http://127.0.0.1:5000/api/readings", code, "test", {}, None)
                self.assertEqual(self.bridge.forward(sample()), expected)
                self.assertEqual(self.sender.call_count, 1)

    def test_transient_api_outage_retries_same_timestamp(self):
        result = self.sender.return_value
        self.sender.side_effect = [URLError("offline"), result]
        payload = sample()
        with patch.object(self.bridge.stopping, "wait", return_value=False):
            self.assertEqual(self.bridge.forward(payload), "stored")
        self.assertEqual(self.sender.call_count, 2)
        for call in self.sender.call_args_list:
            self.assertEqual(call.args[2]["timestamp"], payload["timestamp"])

    def test_api_outage_has_bounded_retries(self):
        self.sender.side_effect = URLError("offline")
        with patch.object(self.bridge.stopping, "wait", return_value=False):
            self.assertEqual(self.bridge.forward(sample()), "unavailable")
        self.assertEqual(self.sender.call_count, 3)
        self.assertEqual(self.bridge.rejected, 1)

    def test_api_token_cannot_be_forwarded_to_remote_http_destination(self):
        for url in ["http://example.com", "https://example.com", "http://localhost.attacker.invalid", "http://127.0.0.1/other", "http://user:pass@localhost"]:
            with self.assertRaises(ValueError):
                MQTTBridge(self.settings, url, TOKEN)

    def test_exact_topic_private_tls_and_credentials_requirements(self):
        for overrides in [{"topic": "#"}, {"topic": "farm/+/readings"}, {"topic": ""}, {"port": 0}, {"public_demo": False}, {"username": "secret"}, {"transport": "invalid"}]:
            with self.assertRaises(ValueError):
                replace(self.settings, **overrides).validate()
        private = replace(self.settings, public_demo=False, tls=True, port=8883, username="device", password="sensitive-password")
        private.validate()
        self.assertNotIn("sensitive-password", repr(private))

    def test_subscription_waits_for_successful_acknowledgement(self):
        self.bridge.on_subscribe(None, None, 1, [SimpleNamespace(is_failure=True)], None)
        self.assertFalse(self.bridge.subscribed.is_set())
        self.bridge.on_subscribe(None, None, 1, [SimpleNamespace(is_failure=False)], None)
        self.assertTrue(self.bridge.subscribed.is_set())
        self.bridge.on_disconnect(None, None, None, 0, None)
        self.assertFalse(self.bridge.subscribed.is_set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
