# Wokwi: complete sketch, no config.h tab

This public-demo variant embeds the non-secret broker/topic configuration in `sketch.ino`. The complete program includes both required Arduino entry points, `setup()` and `loop()`. A configuration-only snippet is not a complete sketch.

The current version defers NTP startup until WiFi has an IP address and includes `[BOOT]`, `[WiFi]` and `[TIME]` messages. In the user's subsequent Wokwi run, startup passed these checkpoints, time synchronized, and three transmitted samples matched SQLite IDs 22–24. No assertion appeared in that supplied run. Long-term reliability remains untested.

1. In Wokwi, select the **sketch.ino** tab. Replace its entire contents with this directory's full `sketch.ino`, from the first include through the final closing brace.
2. Replace **diagram.json** with this directory's `diagram.json`.
3. In **Library Manager**, use the blue plus to add **DHT sensor library**, **Adafruit Unified Sensor**, and **PubSubClient**. Wokwi creates `libraries.txt` automatically.
4. Click **Start Simulation**. No `config.h` tab is needed. Keep the laptop MQTT subscriber running for dashboard updates.

This file uses the topic generated for this workspace. If the laptop topic changes, update the `MQTT_TOPIC` definition in the sketch to match `instance/mqtt-demo.json`. The public anonymous broker is for synthetic readings only. No API token is included.

For your own run, match each Serial timestamp and reading to an accepted record in the subscriber and dashboard. Physical calibration, broader simulator scenarios and long-duration resilience remain unverified. If a later build fails, copy the full build error text, including the rightmost text after `undefined reference`, so the missing symbol can be identified.
