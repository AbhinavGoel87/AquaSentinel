# Sensor controller

Moisture publishing is still later work. Do not assign sensor GPIO pins yet.

The board that drives sprinklers and the irrigation-tank treatment relays is `firmware/field_node`.
Those outputs stay off until their pins are set, and they turn off if the Pi stops answering.
