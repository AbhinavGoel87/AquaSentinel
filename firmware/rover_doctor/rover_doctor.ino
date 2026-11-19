/*
  Kshetra doctor camera — ESP32-CAM

  This board captures a JPEG and POSTs the raw bytes to the computer.
  The computer compares those colors with the example photos in
  plant_database. That is a color match. It is not a trained neural
  net, not a laboratory test, and it does not report a measurement
  or a dose.

  How to flash and run
  --------------------
  1. Install the Arduino IDE. Open File → Preferences and add this
     Boards Manager URL:
       https://espressif.github.io/arduino-esp32/package_esp32_index.json
     Then Tools → Board → Boards Manager, and install "esp32" by
     Espressif Systems. Select Tools → Board → AI Thinker ESP32-CAM.
  2. Edit WIFI_SSID and WIFI_PASSWORD below. The ESP32-CAM and the
     computer must be on the same Wi-Fi. Nothing is sent to a paid cloud.
  3. Edit COMPUTER_URL. Replace 192.168.1.20 with the computer's LAN
     IPv4 address (ipconfig on Windows). The ESP posts to:
       http://COMPUTER_IP:5000/api/inspections
     Content-Type is image/jpeg. The body is the raw JPEG, not a form.
     127.0.0.1 is this computer only, so the ESP cannot use it.
  4. On the computer, from the Kshetra folder, start the app so the
     ESP can reach it. The program still defaults to 127.0.0.1.
     PowerShell:
       $env:KSHETRA_HOST = "0.0.0.0"
       py -3 start.py
     If Windows asks about the firewall, allow Python on private networks.
  5. On the computer open http://127.0.0.1:5000 and open the Doctor tab.
     Each accepted photo shows the color-match report there.
     Serial Monitor is 115200 baud.

  To upload, connect GPIO 0 to GND, tap the reset button, upload, then
  disconnect GPIO 0 and tap reset again so the board runs this sketch.

  Motors stay off. MOTOR_LEFT_PIN and MOTOR_RIGHT_PIN are -1, so those
  GPIO pins are not driven. Set them only after the wiring is checked.
  If Wi-Fi is down, this sketch does not move motors. It forces any
  wired motor pin off and waits.
*/

#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include "esp_camera.h"

// Student edits these three lines.
const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
// Placeholder LAN address. Use the computer's Wi-Fi IPv4, not 127.0.0.1.
const char* COMPUTER_URL = "http://192.168.1.20:5000/api/inspections";

// -1 means "do not touch this pin". Leave both at -1 until the wiring is checked.
const int MOTOR_LEFT_PIN = -1;
const int MOTOR_RIGHT_PIN = -1;

const unsigned long PHOTO_INTERVAL_MS = 20000;

bool cameraReady = false;
bool sawWifi = false;

// Common AI-Thinker ESP32-CAM pins. Change these if your board differs.
bool setupCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_pwdn = 32;
  config.pin_reset = -1;
  config.pin_xclk = 0;
  // The SCCB field name changed in ESP32 board package 3.x. Same pins either way.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
#else
  config.pin_sscb_sda = 26;
  config.pin_sscb_scl = 27;
#endif
  config.pin_d7 = 35;
  config.pin_d6 = 34;
  config.pin_d5 = 39;
  config.pin_d4 = 36;
  config.pin_d3 = 21;
  config.pin_d2 = 19;
  config.pin_d1 = 18;
  config.pin_d0 = 5;
  config.pin_vsync = 25;
  config.pin_href = 23;
  config.pin_pclk = 22;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_DRAM;
  if (psramFound()) {
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;
  }

  const esp_err_t started = esp_camera_init(&config);
  if (started != ESP_OK) {
    Serial.printf("Camera failed to start: 0x%x\n", started);
    Serial.println("Pins above are the common ESP32-CAM. Change them if your board differs.");
    Serial.println("If it still fails, try xclk_freq_hz = 10000000 and a solid 5V supply.");
    return false;
  }

  // The first frame after init is often incomplete. Drop it.
  camera_fb_t* warmup = esp_camera_fb_get();
  if (warmup != nullptr) {
    esp_camera_fb_return(warmup);
  }
  return true;
}

void motorsOff() {
  if (MOTOR_LEFT_PIN >= 0) digitalWrite(MOTOR_LEFT_PIN, LOW);
  if (MOTOR_RIGHT_PIN >= 0) digitalWrite(MOTOR_RIGHT_PIN, LOW);
}

void prepareMotors() {
  if (MOTOR_LEFT_PIN >= 0) pinMode(MOTOR_LEFT_PIN, OUTPUT);
  if (MOTOR_RIGHT_PIN >= 0) pinMode(MOTOR_RIGHT_PIN, OUTPUT);
  motorsOff();
}

bool postPhoto(const uint8_t* data, size_t length) {
  if (WiFi.status() != WL_CONNECTED || data == nullptr || length == 0) {
    motorsOff();
    return false;
  }

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(15000);
  if (!http.begin(client, COMPUTER_URL)) {
    Serial.println("COMPUTER_URL could not be opened. Edit the computer's LAN IP.");
    return false;
  }
  http.addHeader("Content-Type", "image/jpeg");
  const int status = http.POST(const_cast<uint8_t*>(data), length);
  http.end();
  Serial.printf("Photo post status: %d (%u bytes)\n", status, static_cast<unsigned>(length));
  if (WiFi.status() != WL_CONNECTED) motorsOff();
  return status >= 200 && status < 300;
}

void waitBetweenPhotos() {
  const unsigned long start = millis();
  while (millis() - start < PHOTO_INTERVAL_MS) {
    if (WiFi.status() != WL_CONNECTED) {
      motorsOff();
      sawWifi = false;
      return;
    }
    delay(250);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  prepareMotors();
  cameraReady = setupCamera();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Doctor camera booted. Motors are off.");
  Serial.println("Edit WIFI_SSID, WIFI_PASSWORD, and COMPUTER_URL, then flash again.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    motorsOff();
    sawWifi = false;
    Serial.println("Wi-Fi is down. Motors stay off.");
    delay(1000);
    return;
  }

  if (!sawWifi) {
    WiFi.setSleep(false);
    sawWifi = true;
    Serial.print("Wi-Fi connected. Board IP ");
    Serial.println(WiFi.localIP());
    Serial.print("Posting JPEG to ");
    Serial.println(COMPUTER_URL);
  }

  if (!cameraReady) {
    motorsOff();
    delay(2000);
    return;
  }

  camera_fb_t* frame = esp_camera_fb_get();
  if (frame != nullptr) {
    if (frame->format == PIXFORMAT_JPEG && frame->len > 0) {
      const bool accepted = postPhoto(frame->buf, frame->len);
      if (accepted) {
        Serial.println("Computer accepted the photo. Open the Doctor tab to read the color match.");
      } else {
        Serial.println("Photo was not accepted. Check the computer is running with KSHETRA_HOST=0.0.0.0.");
      }
    } else {
      Serial.println("Camera frame was not a JPEG.");
    }
    esp_camera_fb_return(frame);
  } else {
    Serial.println("Camera did not capture a frame.");
  }

  motorsOff();
  waitBetweenPhotos();
}
