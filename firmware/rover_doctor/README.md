# Doctor camera — ESP32-CAM

This board takes a JPEG and sends the raw bytes to the computer over Wi-Fi.
The computer compares the photo with `plant_database`. That comparison is a color match to the example photos. It is not a trained neural net, not a laboratory test, and it does not report a measurement or a dose.

The sketch does not choose a treatment and it does not open a sprinkler. Motor pins stay at `-1`, so they are not driven. If Wi-Fi drops, any motor pin you later set is forced off and the board does not move.

The camera pins in `rover_doctor.ino` are the common AI-Thinker ESP32-CAM pins. Change those numbers if your board differs.

## Same Wi-Fi, no paid cloud

The ESP32-CAM and the computer join the same Wi-Fi network. The photo is posted on that network. There is no cloud account and no paid service.

## 1. Install ESP32 board support

1. Install the Arduino IDE.
2. File → Preferences → Additional boards manager URLs. Add:

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

3. Tools → Board → Boards Manager. Install **esp32** by Espressif Systems.
4. Tools → Board → **AI Thinker ESP32-CAM**.
5. Tools → Port → the board's COM port. Serial Monitor baud is **115200**.

To upload on a typical ESP32-CAM: connect GPIO 0 to GND, tap reset, click Upload, then disconnect GPIO 0 and tap reset so the sketch runs.

## 2. Fill in Wi-Fi and the computer IP

Open `firmware/rover_doctor/rover_doctor.ino` and edit the three placeholders:

| Line | Set it to |
| --- | --- |
| `WIFI_SSID` | The Wi-Fi name |
| `WIFI_PASSWORD` | The Wi-Fi password |
| `COMPUTER_URL` | `http://` + the computer's LAN IPv4 + `:5000/api/inspections` |

Find the computer's address with `ipconfig` (Windows) and use the Wi-Fi adapter's IPv4 address. Example, if that address is `192.168.1.20`:

```text
http://192.168.1.20:5000/api/inspections
```

`127.0.0.1` is the computer talking to itself. The ESP cannot reach that address. Leave `MOTOR_LEFT_PIN` and `MOTOR_RIGHT_PIN` at `-1`.

The POST body is the raw JPEG. The header is `Content-Type: image/jpeg`.

## 3. Start the app so the ESP can reach it

The app binds `127.0.0.1` by default. Leave that default in the code. For this session, from the Kshetra folder in PowerShell:

```powershell
$env:KSHETRA_HOST = "0.0.0.0"
py -3 start.py
```

`0.0.0.0` listens on the LAN as well as on this computer. If Windows Firewall asks, allow Python on private networks. Port `5000` must be reachable from the ESP.

## 4. Read the classification

On the computer open http://127.0.0.1:5000 and open the **Doctor** tab. After each photo the page shows the closest plant-database match and the farmer message. The serial monitor prints the HTTP status. A status from 200 to 299 means the computer accepted the JPEG.

The board then waits 20 seconds and takes another photo. If Wi-Fi drops during that wait, motors stay off and the next photo waits until Wi-Fi returns.
