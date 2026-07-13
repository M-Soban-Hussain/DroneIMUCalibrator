import requests
import time

PHYPHOX_IP = "192.168.1.9"
PORT = 8080

URL = f"http://{PHYPHOX_IP}:{PORT}/get?accX&accY&accZ&gyrX&gyrY&gyrZ"

print("Connecting to Phyphox...\n")

while True:
    try:
        response = requests.get(URL, timeout=1)
        data = response.json()

        b = data["buffer"]

        ax = b["accX"]["buffer"][0]
        ay = b["accY"]["buffer"][0]
        az = b["accZ"]["buffer"][0]

        gx = b["gyrX"]["buffer"][0]
        gy = b["gyrY"]["buffer"][0]
        gz = b["gyrZ"]["buffer"][0]

        print(
            f"\r"
            f"AX:{ax:7.3f}  "
            f"AY:{ay:7.3f}  "
            f"AZ:{az:7.3f}   |   "
            f"GX:{gx:7.3f}  "
            f"GY:{gy:7.3f}  "
            f"GZ:{gz:7.3f}",
            end=""
        )

        time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nStopped.")
        break

    except Exception as e:
        print("\nError:", e)
        time.sleep(1)