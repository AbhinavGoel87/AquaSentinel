# Doctor rover — ESP32-CAM

This board takes the plant photo and sends it to the Raspberry Pi.
It does not decide the plant's health and it does not open a sprinkler.

Before you flash:

1. Set the Wi-Fi name and password.
2. Set `PI_URL` to the Pi, for example `http://192.168.1.20:5000/api/inspections`.
3. Leave the motor pins at `-1` until you have checked the wiring.
   A pin left at `-1` is not driven, so the sketch cannot spin a motor by accident.

The camera model below is the common ESP32-CAM board. If your board is different, change the pin numbers in `camera_config` before flashing.

On startup the motors stay off. If the Pi cannot be reached, the motors stay off.
The photo upload uses HTTP. The Pi compares the photo with `plant_database`.
