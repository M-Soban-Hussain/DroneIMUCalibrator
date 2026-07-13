import threading
import time
import requests
import serial
import serial.tools.list_ports
import os

# ==========================================================
# Shared Data
# ==========================================================

fc = {
    "ax": 0.0,
    "ay": 0.0,
    "az": 0.0,
    "gx": 0.0,
    "gy": 0.0,
    "gz": 0.0
}

phone = {
    "ax": 0.0,
    "ay": 0.0,
    "az": 0.0,
    "gx": 0.0,
    "gy": 0.0,
    "gz": 0.0
}

# Change this if your phone IP changes
PHYPHOX_IP = "192.168.1.9"

PHY_URL = (
    f"http://{PHYPHOX_IP}:8080/get?"
    "accX&accY&accZ&gyrX&gyrY&gyrZ"
)


# ==========================================================
# Find STM32
# ==========================================================

def find_stm32():

    while True:

        ports = serial.tools.list_ports.comports()

        for p in ports:

            desc = p.description.lower()

            if (
                "stm32" in desc or
                "virtual com" in desc or
                "cdc" in desc
            ):
                print(f"STM32 Found : {p.device}")
                return p.device

        print("Waiting for STM32...")
        time.sleep(1)


# ==========================================================
# STM32 Thread
# ==========================================================

def stm32_thread():

    port = find_stm32()

    ser = serial.Serial(port, 115200, timeout=1)

    while True:

        try:

            line = ser.readline().decode(errors="ignore").strip()

            if not line:
                continue

            ax, ay, az, gx, gy, gz = map(float, line.split(","))

            fc["ax"] = ax
            fc["ay"] = ay
            fc["az"] = az
            fc["gx"] = gx
            fc["gy"] = gy
            fc["gz"] = gz

        except:
            pass


# ==========================================================
# Phyphox Thread
# ==========================================================

def phyphox_thread():

    session = requests.Session()

    while True:

        try:

            r = session.get(PHY_URL, timeout=2)

            b = r.json()["buffer"]

            phone["ax"] = b["accX"]["buffer"][0]
            phone["ay"] = b["accY"]["buffer"][0]
            phone["az"] = b["accZ"]["buffer"][0]

            phone["gx"] = b["gyrX"]["buffer"][0]
            phone["gy"] = b["gyrY"]["buffer"][0]
            phone["gz"] = b["gyrZ"]["buffer"][0]

        except:
            pass

        time.sleep(0.02)


# ==========================================================
# Main
# ==========================================================

threading.Thread(target=stm32_thread, daemon=True).start()
threading.Thread(target=phyphox_thread, daemon=True).start()

while True:

    os.system("cls")

    print("=" * 72)
    print("                 DRONE IMU CALIBRATOR  V1")
    print("=" * 72)

    print()

    print("{:<8}{:>14}{:>16}{:>16}".format(
        "Axis",
        "STM32",
        "Phone",
        "Difference"))

    print("-" * 72)

    labels = ["ax", "ay", "az", "gx", "gy", "gz"]

    for x in labels:

        diff = abs(fc[x] - phone[x])

        print("{:<8}{:>14.3f}{:>16.3f}{:>16.3f}".format(
            x.upper(),
            fc[x],
            phone[x],
            diff))

    print()

    accel_error = (
        abs(fc["ax"] - phone["ax"]) +
        abs(fc["ay"] - phone["ay"]) +
        abs(fc["az"] - phone["az"])
    ) / 3

    gyro_error = (
        abs(fc["gx"] - phone["gx"]) +
        abs(fc["gy"] - phone["gy"]) +
        abs(fc["gz"] - phone["gz"])
    ) / 3

    print(f"Average Accelerometer Error : {accel_error:.4f} m/s²")
    print(f"Average Gyroscope Error     : {gyro_error:.4f} rad/s")

    time.sleep(0.1)