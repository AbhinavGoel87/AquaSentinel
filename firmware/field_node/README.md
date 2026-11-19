# Field controller

The field, its soil sensors, and the Arduino Uno are a separate system. Kshetra does not connect to them. There is no Bluetooth link, and this app does not open sprinklers or nutrient valves.

`field_node.ino` is an older ESP32 sketch from when this computer tried to drive those outputs. Do not flash it for the current Kshetra doctor. The doctor only receives photos from `firmware/rover_doctor`.
