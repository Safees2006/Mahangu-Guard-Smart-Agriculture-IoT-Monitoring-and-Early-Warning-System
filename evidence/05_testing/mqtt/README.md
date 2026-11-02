# MQTT evidence — 2 November 2026, Asia/Colombo

`automated_tests.txt` records actual backend/MQTT boundary tests. `P09_mqtt_trace.json` records a real Python synthetic publication through **broker.hivemq.com:1883**, the accepted Flask response, matching SQLite row and dashboard overview. Its `screenshot_sample` identifies the second actual MQTT publication shown in the screenshots (18% moisture and 42°C).

The two `P09_mqtt_demo_dashboard_*.png` files are genuine desktop/mobile Edge captures of readings delivered through that MQTT path. Browser outcomes are in `browser_checks.txt`. The sample source is `mqtt_demo`, not `wokwi_simulation`.

An earlier attempt against test.mosquitto.org:1883 timed out. `last_failure.json`, if present, preserves that earlier failure and its timestamp; it does not supersede the later successful HiveMQ trace. The port check found HiveMQ TCP 1883 reachable and the demo configuration was updated accordingly.

This proves Python MQTT publisher → real broker → subscriber → authenticated loopback HTTP → SQLite → overview/dashboard. It does **not** establish Wokwi compilation, ESP32 execution, real soil measurements, authenticated publishers on the public broker or private-broker TLS deployment. Capture separate P08 serial/circuit evidence and a matching P09 sample after actually running Wokwi.
