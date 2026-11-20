# Status

The running app is the plant doctor.

## Done

- A local Flask page that receives a JPEG from the ESP32-CAM or from the file picker.
- Color match against the CoLeaf examples, with a sureness percentage for every entry.
- A confirmed timer, **Add to irrigation**, stored on this computer. It does not open a valve.
- ESP32-CAM sketch that posts the JPEG over Wi-Fi. Motor pins stay off.

## Not part of this app

- The field, soil sensors, sprinklers, and the Arduino Uno. Those stay on their own system.
- A laboratory nutrient test, a neural net, or a cloud API.
