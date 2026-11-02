#include <Arduino.h>
#include <esp_system.h>
// Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <time.h>
// Public-demo configuration: no config.h tab required.
#define MQTT_HOST "broker.hivemq.com"
#define MQTT_PORT 1883
#define MQTT_TOPIC "mahangu-guard/demo/b3c8afdb4dfb76827d957b8b/mahangu-01/readings"
#define DEVICE_ID "mahangu-01"
#define MQTT_USE_TLS 0
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""
#define MQTT_ROOT_CA ""

constexpr int MOISTURE_PIN = 34, PH_PIN = 35, ALKALINITY_PIN = 32;
constexpr int LIGHT_PIN = 33, DHT_PIN = 15, LED_PIN = 25, BUZZER_PIN = 26;
DHT dht(DHT_PIN, DHT22);
#if MQTT_USE_TLS
WiFiClientSecure network;
#else
WiFiClient network;
#endif
PubSubClient mqtt(network);
unsigned long lastSample = 0, lastAttempt = 0, lastWifiAttempt = 0;
String clientId;
bool configurationOK = true;
bool timeServiceStarted = false;
bool wifiConnectionReported = false;
bool timeSyncReported = false;

void setup() {
  Serial.begin(115200);
  Serial.println("Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System");
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  analogReadResolution(12);
  dht.begin();
  Serial.println("SIMULATION: moisture, pH, alkalinity are analogue proxies. No physical farm calibration.");
  if (String(MQTT_TOPIC).indexOf("REPLACE_") >= 0) {
    Serial.println("Run mqtt_setup.py and copy its generated config.h into Wokwi.");
    configurationOK = false;
  }
#if MQTT_USE_TLS
  if (strlen(MQTT_ROOT_CA) == 0) {
    Serial.println("TLS requires a trusted broker root CA in MQTT_ROOT_CA.");
    configurationOK = false;
  } else network.setCACert(MQTT_ROOT_CA);
#else
  if (strlen(MQTT_USERNAME) || strlen(MQTT_PASSWORD)) {
    Serial.println("Use TLS for broker credentials. Anonymous synthetic demo only on plain MQTT.");
    configurationOK = false;
  }
#endif
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  if (!mqtt.setBufferSize(1024)) {
    Serial.println("MQTT packet buffer allocation failed.");
    configurationOK = false;
  }
  mqtt.setSocketTimeout(3);
  mqtt.setKeepAlive(30);
  Serial.println("[BOOT] MQTT client configured");
  clientId = "mg-wokwi-" + String((uint32_t)esp_random(), HEX);
  Serial.println("[BOOT] Client ID ready; starting WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin("Wokwi-GUEST", "", 6);
  Serial.println("[BOOT] WiFi start requested; waiting for an IP address");
  // Start SNTP later, after WiFi has connected and acquired an IP address.
}

void serviceNetwork() {
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnectionReported = false;
    if (millis() - lastWifiAttempt >= 15000) {
      Serial.println("[WiFi] Not connected; retrying");
      WiFi.reconnect();
      lastWifiAttempt = millis();
    }
    return;
  }
  if (WiFi.localIP() == IPAddress(0, 0, 0, 0)) return;
  if (!wifiConnectionReported) {
    Serial.print("[WiFi] Connected; IP=");
    Serial.println(WiFi.localIP());
    wifiConnectionReported = true;
  }
  if (!timeServiceStarted) {
    Serial.println("[TIME] Starting NTP after WiFi is ready");
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    timeServiceStarted = true;
    Serial.println("[TIME] NTP start returned");
  }
  if (!timeSyncReported && time(nullptr) >= 1700000000) {
    Serial.println("[TIME] Clock synchronized");
    timeSyncReported = true;
  }
}

void serviceMqtt() {
  if (!configurationOK || WiFi.status() != WL_CONNECTED) return;
#if MQTT_USE_TLS
  if (time(nullptr) < 1700000000) return;
#endif
  if (!mqtt.connected() && millis() - lastAttempt >= 5000) {
    lastAttempt = millis();
    bool connected = strlen(MQTT_USERNAME)
      ? mqtt.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)
      : mqtt.connect(clientId.c_str());
    if (connected) Serial.println("[MQTT] CONNECTED");
    else Serial.printf("[MQTT] OFFLINE state=%d; retrying later\n", mqtt.state());
  }
  if (mqtt.connected()) mqtt.loop();
}

void loop() {
  serviceNetwork();
  serviceMqtt();
  if (millis() - lastSample < 5000) { delay(10); return; }
  lastSample = millis();
  float moisture = analogRead(MOISTURE_PIN) * 100.0 / 4095;
  float ph = analogRead(PH_PIN) * 14.0 / 4095;
  float alkalinity = analogRead(ALKALINITY_PIN) * 1000.0 / 4095;
  float light = 100.0 - analogRead(LIGHT_PIN) * 100.0 / 4095;
  float temperature = dht.readTemperature();
  if (isnan(temperature)) {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("Sensor read failed; no sample published.");
    return;
  }
  bool dry = moisture < 30, wet = moisture > 85, hot = temperature > 38;
  bool phWarning = ph < 5.5 || ph > 7.5, alkWarning = alkalinity > 200;
  bool alert = dry || wet || hot || phWarning || alkWarning;
  digitalWrite(LED_PIN, alert ? HIGH : LOW);
  if (alert) tone(BUZZER_PIN, 880, 180);
  Serial.printf("LOCAL dry=%d wet=%d heat=%d ph=%d alkalinity=%d\n", dry, wet, hot, phWarning, alkWarning);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi offline; local warnings active.");
    return;
  }
  time_t now = time(nullptr);
  if (now < 1700000000) { Serial.println("Waiting for network time; sample not published."); return; }
  char timestamp[28];
  struct tm utc;
  gmtime_r(&now, &utc);
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
  String payload = "{\"device_id\":\"" DEVICE_ID "\",\"timestamp\":\"" + String(timestamp) +
    "\",\"source\":\"wokwi_simulation\",\"moisture\":" + String(moisture, 1) +
    ",\"temperature\":" + String(temperature, 1) + ",\"ph\":" + String(ph, 2) +
    ",\"light\":" + String(light, 1) + ",\"alkalinity\":" + String(alkalinity, 1) + "}";
  Serial.println(payload);
  if (mqtt.connected() && mqtt.publish(MQTT_TOPIC, payload.c_str(), false)) {
    Serial.println("[MQTT] SENT (QoS 0; confirm accepted ID in laptop bridge and dashboard)");
  } else Serial.println("[MQTT] NOT SENT; local warning still shown");
}
