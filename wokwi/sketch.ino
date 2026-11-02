// Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <time.h>
#include "config.h"

// Percent / pH / alkalinity are analogue proxies, not calibrated measurements.
constexpr int MOISTURE_PIN = 34, PH_PIN = 35, ALKALINITY_PIN = 32;
constexpr int LIGHT_PIN = 33, DHT_PIN = 15, LED_PIN = 25, BUZZER_PIN = 26;
DHT dht(DHT_PIN, DHT22);
unsigned long lastSample = 0, lastReconnect = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("Mahangu Guard – Smart Agriculture IoT Monitoring and Early Warning System");
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  analogReadResolution(12);
  dht.begin();
  WiFi.begin("Wokwi-GUEST", "", 6);
  configTime(0, 0, "pool.ntp.org");
  Serial.println("SIMULATION ONLY: soil pH and alkalinity use potentiometers.");
}

void loop() {
  if (millis() - lastSample < 5000) return;
  lastSample = millis();
  float moisture = analogRead(MOISTURE_PIN) * 100.0 / 4095;
  float ph = analogRead(PH_PIN) * 14.0 / 4095;
  float alkalinity = analogRead(ALKALINITY_PIN) * 1000.0 / 4095;
  float light = 100.0 - analogRead(LIGHT_PIN) * 100.0 / 4095;
  float temperature = dht.readTemperature();
  if (isnan(temperature)) {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("DHT read failed; no sample transmitted.");
    return;
  }
  bool alert = moisture < 30 || moisture > 85 || temperature > 38 || ph < 5.5 || ph > 7.5 || alkalinity > 200;
  digitalWrite(LED_PIN, alert ? HIGH : LOW);
  if (alert) tone(BUZZER_PIN, 880, 180);
  // Local warnings continue even when networking or time synchronisation fails.
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi offline; local warning logic remains active.");
    if (millis() - lastReconnect > 15000) { WiFi.reconnect(); lastReconnect = millis(); }
    return;
  }
  time_t now = time(nullptr);
  if (now < 1700000000) { Serial.println("Waiting for network time; not posting an invalid timestamp."); return; }
  char timestamp[28];
  struct tm utc;
  gmtime_r(&now, &utc);
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
  String payload = "{\"device_id\":\"" DEVICE_ID "\",\"timestamp\":\"" + String(timestamp) +
    "\",\"source\":\"wokwi_simulation\",\"moisture\":" + String(moisture, 1) +
    ",\"temperature\":" + String(temperature, 1) + ",\"ph\":" + String(ph, 2) +
    ",\"light\":" + String(light, 1) + ",\"alkalinity\":" + String(alkalinity, 1) + "}";
  Serial.println(payload); // Credentials are never printed.
  HTTPClient http;
  WiFiClient localClient;
  WiFiClientSecure tlsClient;
  bool secure = String(API_URL).startsWith("https://");
  if (secure) {
    // Configure a trusted root CA before using an HTTPS tunnel.
    // Verification is deliberately not disabled with setInsecure().
    Serial.println("HTTPS requires a trusted root CA: configure tlsClient.setCACert(...) first.");
    return;
  }
  if (!String(API_URL).startsWith("http://host.wokwi.internal:")) {
    Serial.println("Plain HTTP restricted to the local private gateway.");
    return;
  }
  http.setTimeout(3000);
  if (!http.begin(localClient, API_URL)) { Serial.println("HTTP setup failed."); return; }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " DEVICE_TOKEN);
  int code = http.POST(payload);
  Serial.printf("API delivery HTTP %d (201 = stored)\n", code);
  Serial.println(http.getString());
  http.end();
}
