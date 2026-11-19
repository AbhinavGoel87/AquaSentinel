/*
  Kshetra field node.

  Polls the Raspberry Pi and mirrors sprinkler and treatment outputs.
  Pins stay unwired while they are -1.
  Three missed polls turn every wired output off.
*/

#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* OUTPUTS_URL = "http://192.168.1.20:5000/api/outputs";

// Set a pin only after that relay is wired and checked.
const int ZONE1_PIN = -1;
const int ZONE2_PIN = -1;
const char* NUTRIENT_IDS[] = {
  "boron", "calcium", "iron", "magnesium", "manganese", "nitrogen", "phosphorus", "potassium"
};
const int NUTRIENT_PINS[] = {-1, -1, -1, -1, -1, -1, -1, -1};
const int NUTRIENT_COUNT = 8;

int missedPolls = 0;

void writePin(int pin, bool on) {
  if (pin >= 0) digitalWrite(pin, on ? HIGH : LOW);
}

void allOff() {
  writePin(ZONE1_PIN, false);
  writePin(ZONE2_PIN, false);
  for (int index = 0; index < NUTRIENT_COUNT; index++) writePin(NUTRIENT_PINS[index], false);
}

void prepare(int pin) {
  if (pin < 0) return;
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

bool flagFor(const String& body, const char* zoneId) {
  const int at = body.indexOf(zoneId);
  if (at < 0) return false;
  const int flag = body.indexOf("\"on\"", at);
  if (flag < 0 || flag > at + 48) return false;
  const int yes = body.indexOf("true", flag);
  return yes >= 0 && yes < flag + 16;
}

bool treatmentFor(const String& body, const char* treatmentId) {
  const int at = body.indexOf("\"treatment\"");
  if (at < 0) return false;
  const int named = body.indexOf(treatmentId, at);
  if (named < 0) return false;
  const int empty = body.indexOf("null", at);
  return empty < 0 || empty > named;
}

void apply(const String& body) {
  if (body.indexOf("\"emergency_stop\": true") >= 0 || body.indexOf("\"emergency_stop\":true") >= 0) {
    allOff();
    return;
  }
  writePin(ZONE1_PIN, flagFor(body, "zone1"));
  writePin(ZONE2_PIN, flagFor(body, "zone2"));
  for (int index = 0; index < NUTRIENT_COUNT; index++) {
    writePin(NUTRIENT_PINS[index], treatmentFor(body, NUTRIENT_IDS[index]));
  }
}

void setup() {
  Serial.begin(115200);
  prepare(ZONE1_PIN);
  prepare(ZONE2_PIN);
  for (int index = 0; index < NUTRIENT_COUNT; index++) prepare(NUTRIENT_PINS[index]);
  allOff();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Field node booted. Outputs are off.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    missedPolls += 1;
    if (missedPolls >= 3) allOff();
    delay(1000);
    return;
  }
  HTTPClient http;
  http.begin(OUTPUTS_URL);
  const int status = http.GET();
  if (status == 200) {
    apply(http.getString());
    missedPolls = 0;
  } else {
    missedPolls += 1;
    if (missedPolls >= 3) allOff();
  }
  http.end();
  delay(1000);
}
