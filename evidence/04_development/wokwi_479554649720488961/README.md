# Shared Wokwi project and actual backend reception

Date: 2 November 2026, Asia/Colombo.

Shared project: https://wokwi.com/projects/479554649720488961 . The public project source was fetched and the 157-line sketch was compared with the local single-file sketch. After newline normalization, they matched exactly, including deferred NTP startup and boot-stage diagnostics. All three required libraries were present in the shared project.

Actual MQTT dashboard database inspection found **20 readings labelled `wokwi_simulation`**, in addition to one earlier `mqtt_demo` sample. The captured latest row is ID 21: sample time `2026-11-02T05:40:02+00:00`, receipt time `2026-11-02T05:41:40.464278+00:00`, moisture 57%, temperature 30°C, pH 6.64, light 75.6%, and synthetic alkalinity 474 mg/L as CaCO₃. The SQLite row was matched by ID, timestamp and value to the actual `/api/overview` response. See `P09_wokwi_backend_trace.json`.

`P09_wokwi_dashboard_received_2026-11-02.png` is a genuine browser screenshot of that local dashboard. It honestly shows **Stale data**, because the latest sample is older than the 20-second threshold, and **High demo alkalinity**, because 474 exceeds the demonstration limit of 200. It is evidence of received/stored history, not continuous current connectivity. `rendered_dashboard.json` records the rendered values at capture time; the UI rounds pH to one decimal place.

The public broker does not authenticate publishers: `wokwi_simulation` is a self-reported source label. No physical soil measurement or authenticated device identity is established. The browser-side attempt to run the shared project did not yield readable serial output; compilation/startup on that browser is not claimed as verified. The original user screenshot independently demonstrated compilation and a startup assertion for the earlier version. A fresh matching serial/circuit capture is still needed to prove which simulator session produced the samples and confirm the updated version's crash behaviour.

## Later user-supplied run: startup and sample correlation verified

The user subsequently pasted fresh Serial output showing all boot checkpoints, WiFi connection, NTP synchronization, MQTT connection and three `[MQTT] SENT` events. No assertion appears in this supplied run. `P08_user_supplied_serial_2026-11-02.txt` preserves the relevant output with normalized line breaks. All three published timestamps (05:55:39, 05:55:44 and 05:55:49 UTC) and sensor values matched independently inspected SQLite rows **22, 23 and 24**. `P09_user_serial_matching_samples_2026-11-02.json` records the comparison and actual dashboard overview at verification time.

This later evidence verifies the startup correction and the Wokwi → public MQTT → local bridge → SQLite path for the observed three samples. The earlier screenshot above remains an earlier, stale snapshot, and should not be relabelled as showing these later sample IDs. Full circuit/serial screenshots, longer resilience testing, calibrated sensors and authenticated private-broker operation remain separate work.
