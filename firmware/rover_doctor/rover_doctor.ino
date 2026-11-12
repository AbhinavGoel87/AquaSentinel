/*
  AquaSentinel doctor rover.

  Takes a JPEG and posts it to the Raspberry Pi.
  Motors stay off unless MOTOR_LEFT_PIN and MOTOR_RIGHT_PIN are set
  to real GPIO numbers after the wiring is checked.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* PI_URL = "http://192.168.1.20:5000/api/inspections";

// Set these only after the motor driver wiring is known.
// -1 means "do not touch this pin".
const int MOTOR_LEFT_PIN = -1;
const int MOTOR_RIGHT_PIN = -1;

const unsigned long PHOTO_INTERVAL_MS = 20000;

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_pwdn = 32;
  config.pin_reset = -1;
  config.pin_xclk = 0;
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
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
  const esp_err_t started = esp_camera_init(&config);
  if (started != ESP_OK) {
    Serial.printf("Camera failed to start: 0x%x\n", started);
  }
}

void motorsOff() {
  if (MOTOR_LEFT_PIN >= 0) digitalWrite(MOTOR_LEFT_PIN, LOW);
  if (MOTOR_RIGHT_PIN >= 0) digitalWrite(MOTOR_RIGHT_PIN, LOW);
}

bool postPhoto(const uint8_t* data, size_t length) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(PI_URL);
  http.addHeader("Content-Type", "image/jpeg");
  const int status = http.POST(const_cast<uint8_t*>(data), length);
  http.end();
  Serial.printf("Photo post status: %d\n", status);
  return status >= 200 && status < 300;
}

void setup() {
  Serial.begin(115200);
  if (MOTOR_LEFT_PIN >= 0) pinMode(MOTOR_LEFT_PIN, OUTPUT);
  if (MOTOR_RIGHT_PIN >= 0) pinMode(MOTOR_RIGHT_PIN, OUTPUT);
  motorsOff();
  setupCamera();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Doctor rover booted. Motors are off.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    motorsOff();
    delay(1000);
    return;
  }
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame != nullptr) {
    postPhoto(frame->buf, frame->len);
    esp_camera_fb_return(frame);
  }
  motorsOff();
  delay(PHOTO_INTERVAL_MS);
}
