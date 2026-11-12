# Field node — ESP32

This board asks the Raspberry Pi what should be on, then drives the sprinkler and treatment relays.

Leave every pin at `-1` until the wiring is checked. A pin left at `-1` is never driven.
On startup, and after three missed answers from the Pi, every wired output is turned off.

The treatment output only follows a cycle the farmer already confirmed on the Pi.
This sketch does not choose a dose and it does not name a product.
Wire the relays so a power loss leaves the sprinklers and the treatment valves closed.
