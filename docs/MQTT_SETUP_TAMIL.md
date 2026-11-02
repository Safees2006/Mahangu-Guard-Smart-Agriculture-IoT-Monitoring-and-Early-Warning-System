# MQTT moolam Wokwi → dashboard

MQTT support serkkappattulladhu. Wokwi paid private gateway thevai illai; public internet broker-ai ESP32-um laptop-um connect seyyum.

```text
Wokwi ESP32 → HiveMQ broker → laptop Python subscriber → Flask → SQLite → dashboard
```

## 1. Laptop-la start pannunga

Project folder terminal-la:

```powershell
.\.venv\Scripts\python.exe mqtt_setup.py
.\.venv\Scripts\python.exe mqtt_bridge.py --public-demo --serve
```

Browser-la **http://127.0.0.1:5050** open pannunga. Terminal-ai close panna vendaam.

## 2. Wokwi-la indha naangu files-ai copy pannunga

[ESP32 project](https://wokwi.com/projects/new/esp32) open seydhu, **wokwi/mqtt/** folder files-ai use pannunga:

| Local file | Wokwi tab |
| --- | --- |
| wokwi/mqtt/sketch.ino | sketch.ino |
| wokwi/mqtt/diagram.json | diagram.json |
| wokwi/mqtt/libraries.txt | libraries.txt |
| wokwi/mqtt/config.h (setup uruvaakkiyadhu) | config.h |

`config.h.example` placeholder file-ai vida, generated `config.h` file-ai copy pannunga. Parent `wokwi/` folder-la irukkira pazhaiya HTTP sketch-udan mix panna vendaam.

## 3. Run pannunga

▶ click pannunga. Network time ready aana pinbu JSON publish aagum. Serial-la `[MQTT] CONNECTED`, `[MQTT] SENT` varugiradhaa paarunga. Laptop subscriber-la `stored id=...` vandhu, adhe timestamp dashboard history-la therindhaal andha reading backend varai vandhadhu urudhi.

Moisture knob-ai kuraithaal dry-soil warning; DHT22 temperature-ai 42°C aakkinaal heat warning varavendum. Screenshots-ai actual run-il mattum edunga.

## Wokwi illaamal MQTT path test

Vera terminal-la:

```powershell
.\.venv\Scripts\python.exe mqtt_demo.py --public-demo --scenario dry
```

Idhu **Python MQTT demo**; Wokwi evidence alla. Dashboard source label `MQTT demo · synthetic` endru kaattum.

Public broker-la real farm data, personal details, password alladhu local API token anuppa vendaam. Random topic security password alla. Real MQTT Python test vetri pettrulladhu. Pinnar user anuppiya Wokwi Serial output-il startup, time sync matrum moonru samples confirm aayina; adhe timestamps/values SQLite IDs 22–24-udan match aayina. Physical sensor calibration matrum neenda-nera reliability innum pending.
