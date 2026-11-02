"""Repeatable contract, persistence and freshness checks; no external services."""
import csv
from datetime import timedelta
import io
from html import escape
from pathlib import Path
import re
import tempfile
import unittest

from app import create_app, utcnow
from feeder import sample

TOKEN = "test-only-token-with-at-least-24-characters"


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = {"TESTING": True, "DATABASE": str(Path(self.temp.name) / "test.sqlite3"), "DEVICE_TOKEN": TOKEN}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + TOKEN}

    def tearDown(self):
        self.temp.cleanup()

    def post(self, data):
        return self.client.post("/api/readings", json=data, headers=self.headers)

    def test_workspace_pages_have_distinct_content_and_active_navigation(self):
        pages = [
            ("/", "dashboard", "Dashboard", 'id="overview"'),
            ("/sensors", "sensors", "Soil & sensors", 'id="sensor-catalog"'),
            ("/trends", "trends", "Sensor trends", 'class="page-chart"'),
            ("/warnings", "warnings", "Early warnings", 'class="page-warnings"'),
            ("/history", "history", "Reading history", 'class="page-history"'),
            ("/system", "system", "System information", 'class="system-facts workspace-facts"'),
        ]
        for path, page, title, content in pages:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(f'data-page="{page}"', html)
                self.assertIn(f'<title>{escape(title)} | ', html)
                self.assertIn(content, html)
                active = re.findall(r'<a[^>]+href="([^"]+)"[^>]*aria-current="page"', html)
                self.assertEqual(active, [path, path])
                ids = re.findall(r'\bid="([^"]+)"', html)
                self.assertEqual(len(ids), len(set(ids)), "Duplicate IDs break live updates.")
                if page != "dashboard":
                    self.assertNotIn('class="overview-grid"', html)
                    self.assertIn(f'<h1 id="page-title">{escape(title)}</h1>', html)
                if page != "system":
                    self.assertNotIn('class="system-facts workspace-facts"', html)
        self.assertEqual(self.client.get("/unknown-workspace-page").status_code, 404)

    def test_history_search_is_preserved_and_html_escaped(self):
        query = '\"><script>alert(1)</script>'
        response = self.client.get("/history", query_string={"q": query})
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('name="q"', html)

    def test_T01_valid_sample_matches_ingestion_history_and_overview(self):
        payload = sample()
        response = self.post(payload)
        self.assertEqual(response.status_code, 201)
        stored = response.json["reading"]
        self.assertEqual(stored["alerts"], [])
        self.assertEqual(self.client.get("/api/overview").json["latest"], stored)
        self.assertEqual(self.client.get("/api/readings").json["readings"], [stored])
        for key in ["moisture", "temperature", "ph", "light", "alkalinity"]:
            self.assertEqual(stored[key], payload[key])

    def test_T02_dry_soil(self):
        alerts = self.post(sample("dry")).json["reading"]["alerts"]
        self.assertIn("dry", [a["code"] for a in alerts])

    def test_T03_heat(self):
        alerts = self.post(sample("heat")).json["reading"]["alerts"]
        self.assertIn("heat", [a["code"] for a in alerts])

    def test_T04_missing_field_does_not_insert(self):
        payload = sample()
        del payload["ph"]
        self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(self.client.get("/api/overview").json["count"], 0)

    def test_T05_out_of_range_and_non_numeric_values(self):
        for field, bad in [("moisture", 101), ("temperature", -41), ("light", -1), ("ph", 15), ("alkalinity", 1001), ("moisture", True), ("ph", "6.4"), ("temperature", None), ("light", float("nan")), ("moisture", float("inf")), ("moisture", 10 ** 400)]:
            with self.subTest(field=field, value=str(bad)):
                payload = sample()
                payload[field] = bad
                self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(self.client.get("/api/overview").json["count"], 0)

    def test_T06_old_sample_is_stale_even_after_recent_delivery(self):
        self.assertEqual(self.client.get("/api/overview").json["connection"], "waiting")
        payload = sample()
        payload["timestamp"] = (utcnow() - timedelta(seconds=30)).isoformat()
        self.assertEqual(self.post(payload).status_code, 201)
        result = self.client.get("/api/overview").json
        self.assertEqual(result["connection"], "stale")
        self.assertGreaterEqual(result["age_seconds"], 30)
        self.assertIsNotNone(result["latest"])

    def test_T07_database_survives_new_application_instance(self):
        stored = self.post(sample()).json["reading"]
        restarted = create_app(self.config).test_client()
        self.assertEqual(restarted.get("/api/overview").json["latest"], stored)

    def test_T08_ph_boundaries_and_simulation_provenance(self):
        for ph, expect_warning in [(5.49, True), (5.5, False), (7.5, False), (7.51, True)]:
            payload = sample()
            payload["ph"] = ph
            reading = self.post(payload).json["reading"]
            self.assertEqual(any(a["code"] == "ph" for a in reading["alerts"]), expect_warning)
            self.assertEqual(reading["source"], "local_demo")

    def test_authentication_required(self):
        for auth in [None, "Bearer wrong", "Bearer tést", ""]:
            headers = {"Authorization": auth} if auth is not None else {}
            self.assertEqual(self.client.post("/api/readings", json=sample(), headers=headers).status_code, 401)
        self.assertEqual(self.client.get("/api/overview").json["count"], 0)

    def test_duplicate_rejected_without_double_counting(self):
        payload = sample()
        self.assertEqual(self.post(payload).status_code, 201)
        self.assertEqual(self.post(payload).status_code, 409)
        self.assertEqual(self.client.get("/api/overview").json["count"], 1)

    def test_late_arriving_sample_does_not_replace_newer_sample(self):
        new = self.post(sample()).json["reading"]
        old = sample("dry")
        old["timestamp"] = (utcnow() - timedelta(minutes=2)).isoformat()
        self.assertEqual(self.post(old).status_code, 201)
        self.assertEqual(self.client.get("/api/overview").json["latest"]["id"], new["id"])
        self.assertEqual(self.client.get("/api/readings").json["readings"][-1]["id"], new["id"])

    def test_all_concurrent_warnings_are_returned(self):
        payload = sample("dry")
        payload.update(temperature=42, ph=8.2, alkalinity=250)
        alerts = self.post(payload).json["reading"]["alerts"]
        self.assertEqual({a["code"] for a in alerts}, {"dry", "heat", "ph", "alkalinity"})

    def test_threshold_edges(self):
        for moisture, temperature, alkalinity, expected in [(30, 38, 200, set()), (85, 38, 200, set()), (85.1, 38.1, 200.1, {"wet", "heat", "alkalinity"})]:
            payload = sample()
            payload.update(moisture=moisture, temperature=temperature, alkalinity=alkalinity)
            codes = {a["code"] for a in self.post(payload).json["reading"]["alerts"]}
            self.assertEqual(codes, expected)

    def test_malformed_json_and_content_type_and_size(self):
        self.assertEqual(self.client.post("/api/readings", data="{oops", headers=self.headers, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/readings", data="text", headers=self.headers).status_code, 415)
        self.assertEqual(self.client.post("/api/readings", data="x" * 9000, headers=self.headers, content_type="application/json").status_code, 413)
        for data in [[], None, 1, "bad"]:
            response = self.client.post("/api/readings", data=__import__('json').dumps(data), headers=self.headers, content_type="application/json")
            self.assertEqual(response.status_code, 400)

    def test_device_source_and_timestamp_restrictions(self):
        for changes in [{"device_id": "unknown"}, {"source": []}, {"source": "pretend"}, {"timestamp": "invalid"}, {"timestamp": 4}, {"timestamp": "2026-01-01T00:00:00"}, {"timestamp": "2010-01-01T00:00:00Z"}, {"timestamp": (utcnow() + timedelta(minutes=5)).isoformat()}, {"unexpected": 1}]:
            with self.subTest(changes=changes):
                payload = sample()
                payload.update(changes)
                self.assertEqual(self.post(payload).status_code, 400)

    def test_history_limit_and_csv_export(self):
        stored = self.post(sample()).json["reading"]
        for limit in ["0", "501", "nan", "1.1"]:
            self.assertEqual(self.client.get("/api/readings?limit=" + limit).status_code, 400)
        self.assertEqual(len(self.client.get("/api/readings?limit=1").json["readings"]), 1)
        result = self.client.get("/api/export.csv")
        self.assertEqual(result.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(result.text)))
        self.assertEqual(int(rows[0]["id"]), stored["id"])
        self.assertEqual(rows[0]["source"], "local_demo")

    def test_extreme_timestamp_offsets_are_client_errors(self):
        for timestamp in ["0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"]:
            payload = sample()
            payload["timestamp"] = timestamp
            self.assertEqual(self.post(payload).status_code, 400)

    def test_empty_dashboard_assets_and_weather_status(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mahangu Guard", response.text)
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        for path in ["/static/app.js", "/static/style.css", "/api/health"]:
            result = self.client.get(path)
            self.assertEqual(result.status_code, 200)
            result.close()
        result = self.client.get("/api/overview").json
        self.assertIsNone(result["latest"])
        self.assertEqual(result["weather"]["status"], "not_configured")

    def test_mqtt_mode_displays_its_actual_data_path(self):
        config = dict(self.config, MQTT_MODE=True)
        response = create_app(config).test_client().get("/")
        self.assertIn('data-transport="mqtt"', response.text)
        self.assertIn('MQTT broker', response.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
