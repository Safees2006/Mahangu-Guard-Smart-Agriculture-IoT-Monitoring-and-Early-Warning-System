# Wokwi simulation starter — verification pending

**This is the original direct-HTTP version.** For MQTT without a private Wokwi gateway, use [mqtt/README.md](mqtt/README.md) and the files in `wokwi/mqtt/` instead.

1. Create a new ESP32 Arduino project in Wokwi. Copy `sketch.ino`, `diagram.json` and `libraries.txt` into it.
2. Copy `config.h.example` to a new private `config.h` tab. Start the local backend with `python app.py` and set the config token to the value in your local `instance/device-token`. Never publish the token in a shared project or screenshots; rotate it if exposed.
3. Configure Wokwi's **Private IoT Gateway**. With this gateway, the simulator reaches the laptop using `host.wokwi.internal`, not `localhost`. The standard public gateway does not give access to local services. Consult current official guidance: https://docs.wokwi.com/guides/esp32-wifi . Wokwi for VS Code includes a bundled private gateway: https://docs.wokwi.com/vscode/project-config . Availability may depend on your Wokwi setup.
4. Run the simulation. After Wi-Fi and network time synchronisation, the device should submit a JSON sample every five seconds. Confirm `API delivery HTTP 201`, then match the returned ID and timestamp to `/api/overview`, SQLite and the dashboard. That observation has **not** been made in this workspace.
5. Move the potentiometers to exercise moisture, pH and alkalinity warnings. DHT22 represents temperature; the photoresistor represents relative light. Soil variables are analogue proxies, not calibrated sensors. Firmware runs local LED/buzzer checks before its network checks.

Pin map: moisture 34; pH 35; alkalinity 32; relative light 33; DHT22 15; red LED through 220Ω resistor 25; buzzer 26. Sensors use 3.3V. The diagram and sketch require simulator/compile verification.

The supplied firmware allows plain HTTP only through the local private gateway. HTTPS is explicitly blocked until a trusted root CA is configured in the sketch; do not disable certificate verification. An authenticated HTTPS tunnel is a future alternative requiring proper TLS setup, exposure controls and separate verification. Do not expose the Flask development server publicly as a finished deployment.

Capture P08 for circuit and serial evidence, then P09/E02 for one matching end-to-end sample. The local Python feeder exercises the backend path independently and is not evidence of Wokwi transmission.
