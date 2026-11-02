# Wokwi startup crash: investigation and candidate correction

Date: 2 November 2026 (Asia/Colombo).

The user supplied a genuine Wokwi screenshot showing that the MQTT single-file sketch compiled and began executing. Serial output reached the `SIMULATION: moisture, pH, alkalinity ...` banner, then displayed `assert failed: 0x400f49dd <cached disabled>:334 (<cached disabled>)` and an undecoded backtrace. This demonstrates compilation and startup, not successful sensor sampling or MQTT delivery. It does not identify the source function of the assertion.

Inspection found that the original setup requested WiFi and immediately called `configTime()`, before checking connectivity or acquiring an IP. The candidate correction defers SNTP initialization until WiFi is connected and `localIP()` is nonzero. It follows the ordering in [Espressif's SimpleTime example](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Time/SimpleTime/SimpleTime.ino). New boot messages bracket MQTT configuration, client ID creation, WiFi startup and SNTP startup to identify the failing stage if the crash persists. Network retries remain bounded in frequency, and local warning sampling remains in the main loop.

Both `wokwi/mqtt/sketch.ino` and the generated `wokwi/mqtt_single_file/sketch.ino`, plus their ZIPs, were updated. The exact crash cause is still unconfirmed because the compiled ELF, full decoded stack and shared Wokwi project were not available. This change has not yet been run in Wokwi; do not mark the crash resolved or MQTT telemetry verified until an actual rerun demonstrates it.

## Actual retest received

Later on 2 November 2026 the user supplied the saved project URL and fresh Serial output. The shared source matched the updated local sketch. The new output passed every startup checkpoint, obtained IP `10.10.0.2`, started NTP after WiFi, connected MQTT, synchronized time and sent three telemetry payloads without an assertion in the provided run. The samples at 05:55:39, 05:55:44 and 05:55:49 UTC were independently matched to SQLite IDs **22, 23 and 24**, including moisture 57%, temperature 30°C, pH 6.64, light 75.6% and synthetic alkalinity 474 mg/L.

Evidence: `wokwi_479554649720488961/P08_user_supplied_serial_2026-11-02.txt` and `P09_user_serial_matching_samples_2026-11-02.json`. The startup correction and end-to-end delivery are verified for this observed run. This does not establish long-term stability, the exact decoded cause of the original assertion, field calibration or private-broker authentication. The initial `Waiting for network time` message was followed by successful synchronization, so no fabricated timestamp was transmitted. The alkalinity warning is expected because 474 exceeds the demonstration limit of 200.
