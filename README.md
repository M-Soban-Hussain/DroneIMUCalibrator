my drone is not flying well, it sometimes goes left and sometime treas teh errors too late ,  in order to narrow dowsn the error i wnat to make an automatic sort of calibration for the sensors, i want to as for now i am using only mpu 6050 in the gy87 i want to print their values live as fast as possible from the stm32 over the usb and then using phyphox on my mobile i want to make an app or something that tells me the percentage difference of teh mobile and teh drone fligh controller mounted on te drone , it could be a script or a small software entirely custom amde or if no easier to be sued a similar prebuilt app? or software, teh phyphox and teh fc readings will be sent continously and on teh screen the messages will be to rotate the nsoe doesn pitch to 90 degrees both and etc and then after these messages it show teh percentage irregularities beteween the sensor and teh fc, 

yup lets make it, on my desktop ive made a folder (give em a proper name) we'll put everting in it all teh folder all the libraries that iinstall and everything, so that we can make a good visual idea, also can we make an executable of it that shows everything, i mean everything like the realtme values using matplotlib and dropdown to choose com port for the fc attaced and a place to enter teh ip addres of tehphyphox, but wat doe steh phyphox export live data using usb or not or anything?

Ive made a custom experiment in PhyPhox anmed My IMU Calibrator and added teh Accelerometer and Gyroscope and (consdering that my mobile and laptop are both on the same hoem network, you may use hotspot if there are restrictions on teh internet like university wifi), ive checked the allow remote access from teh setting of the created experiment and it is now showing  Remote access enables , Access this experiment from teh following URL: http://192.168.1.9:8080, lets move on to the next task

i was hoping if we could sjip teh whole vs code thing just use python in the cmd C:\Users\Soban>python --version
I have Python 3.11.9

Run the following things after creating the folder:

cd Desktop\DroneIMUCalibrator
dir 
python -m venv .venv
.venv\Scripts\activate
pip install pyqt6 pyserial matplotlib numpy scipy requests
pip freeze > requirements.txt
type nul > app.py
type nul > gui.py
type nul > serial_reader.py
type nul > phyphox_reader.py
type nul > calibration.py
type nul > plots.py
type nul > config.py
mkdir reports
mkdir assets
mkdir firmware_examples


now open teh live experiment of url of phyphox on laptop

=======================================================================================================================================================

i opened teh url of teh phyphox, there is an export button but it only lets you download teh csv and static valued files it doesnt export live continuous data however when i opened "http://192.168.1.9:8080/config" it showed  "

{"crc32":"9566a693","title":"My IMU Calibrator","localTitle":"My IMU Calibrator","category":"Simple custom experiments","localCategory":"Simple custom experiments","buffers":[{"name":"acc_time","size":0},{"name":"accX","size":0},{"name":"accY","size":0},{"name":"accZ","size":0},{"name":"gyr_time","size":0},{"name":"gyrX","size":0},{"name":"gyrY","size":0},{"name":"gyrZ","size":0}],"inputs":[{"source":"accelerometer","outputs":[{"x":"accX"},{"y":"accY"},{"z":"accZ"},{"t":"acc_time"}]},{"source":"gyroscope","outputs":[{"x":"gyrX"},{"y":"gyrY"},{"z":"gyrZ"},{"t":"gyr_time"}]}],"export":[{"set":"Accelerometer","sources":[{"label":"Time (s)","buffer":"acc_time"},{"label":"Acceleration x (m\/s^2)","buffer":"accX"},{"label":"Acceleration y (m\/s^2)","buffer":"accY"},{"label":"Acceleration z (m\/s^2)","buffer":"accZ"}]},{"set":"Gyroscope","sources":[{"label":"Time (s)","buffer":"gyr_time"},{"label":"Gyroscope x (rad\/s)","buffer":"gyrX"},{"label":"Gyroscope y (rad\/s)","buffer":"gyrY"},{"label":"Gyroscope z (rad\/s)","buffer":"gyrZ"}]}]}

======================================================================================================================================================

now I pasted this in teh browser "http://192.168.1.9:8080/get?accX&accY&accZ&gyrX&gyrY&gyrZ"and it printed without pretty print:
 
{"buffer":{
"accX":{"size":0,"updateMode":"single", "buffer":[-7.6995003E-1]},
"accY":{"size":0,"updateMode":"single", "buffer":[-6.48E-1]},
"accZ":{"size":0,"updateMode":"single", "buffer":[9.8620501E0]},
"gyrX":{"size":0,"updateMode":"single", "buffer":[4.125E-4]},
"gyrY":{"size":0,"updateMode":"single", "buffer":[-6.875E-4]},
"gyrZ":{"size":0,"updateMode":"single", "buffer":[-1.1E-3]}
},
"status":{
"session":"883b13", "measuring":true, "timedRun":false, "countDown":0
}
}

====================================================================================================================================================

Open phyphox_reader.py and paste this:

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

========================================================================================================================================

i ran this script "python phyphox_reader.py" and it printed:

(.venv) C:\Users\Soban\Desktop\DroneIMUCalibrator>python phyphox_reader.py
Connecting to Phyphox...

AX: -0.579  AY: -0.663  AZ:  9.838   |   GX: -0.001  GY: -0.001  GZ:  0.000
Error: HTTPConnectionPool(host='192.168.1.9', port=8080): Max retries exceeded with url: /get?accX&accY&accZ&gyrX&gyrY&gyrZ (Caused by ConnectTimeoutError(<HTTPConnection(host='192.168.1.9', port=8080) at 0x1ff99b4d310>, 'Connection to 192.168.1.9 timed out. (connect timeout=1)'))
AX: -0.577  AY: -0.672  AZ:  9.862   |   GX: -0.001  GY:  0.000  GZ:  0.002

=======================================================================================================================

Im using Send_Telemtry() functipon in teh loop of teh FC STM32 with Hal_Delay(10), the code is :
void Send_Telemetry(void)
{
    char msg[128];

    sprintf(msg,
            "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\r\n",
            Ax,
            Ay,
            Az,
            Gx,
            Gy,
            Gz);

    CDC_Transmit_FS((uint8_t*)msg, strlen(msg));
}
//If the STM32 is sending in ms^-2 then use this formula, if in G's continue reading below for i have addressed taht issue there
===========================================================================================================================================

paste the following into the serial_reader.py:

import serial
import serial.tools.list_ports
import time


def find_stm32_port():
    """
    Automatically find the STM32 USB CDC Virtual COM Port.
    """

    while True:
        ports = serial.tools.list_ports.comports()

        for port in ports:
            desc = port.description.lower()
            hwid = port.hwid.lower()

            # Common USB CDC descriptions
            if (
                "stm32" in desc or
                "virtual com port" in desc or
                "usb serial" in desc or
                "cdc" in desc or
                "vid:pid" in hwid
            ):
                print(f"Found: {port.device} ({port.description})")
                return port.device

        print("Waiting for STM32...")
        time.sleep(1)


def main():

    port_name = find_stm32_port()

    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=115200,      # Ignored by USB CDC but kept for compatibility
            timeout=1
        )

        print(f"\nConnected to {port_name}\n")

        while True:

            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                continue

            try:
                ax, ay, az, gx, gy, gz = map(float, line.split(","))

                print(
                    f"\r"
                    f"AX:{ax:8.3f} "
                    f"AY:{ay:8.3f} "
                    f"AZ:{az:8.3f}   |   "
                    f"GX:{gx:8.3f} "
                    f"GY:{gy:8.3f} "
                    f"GZ:{gz:8.3f}",
                    end=""
                )

            except ValueError:
                print("\nInvalid:", line)

    except KeyboardInterrupt:
        print("\nStopped.")

    except Exception as e:
        print("\nError:", e)


if __name__ == "__main__":
    main()

================================================================================================================================================

when i run python serial_reader.py in the cmd it prints:

(.venv) C:\Users\Soban\Desktop\DroneIMUCalibrator>python serial_reader.py
Found: COM4 (STMicroelectronics Virtual COM Port (COM4))

Connected to COM4

AX:  -0.029 AY:  -0.110 AZ:   1.010   |   GX:   0.069 GY:  -0.189 GZ:  -0.274

==============================================================================================================================================

So basicall the units of Phyphox is in ms^-2 but teh stm32 is sending in G's so i need to convert those to ms^-2 as well

now ive changed the send_telemetry function to:

void Send_Telemetry(void)
{
    char msg[128];

    /* Convert to same units as Phyphox */

    float ax = Ax * 9.80665f;
    float ay = Ay * 9.80665f;
    float az = Az * 9.80665f;

    float gx = Gx * 0.017453293f;
    float gy = Gy * 0.017453293f;
    float gz = Gz * 0.017453293f;

    sprintf(msg,
            "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\r\n",
            ax,
            ay,
            az,
            gx,
            gy,
            gz);

    CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
}

======================================================================================================================================

Run serial_reader.py again. and i got the new output as:

(.venv) C:\Users\Soban\Desktop\DroneIMUCalibrator>python serial_reader.py
Found: COM4 (STMicroelectronics Virtual COM Port (COM4))

Connected to COM4

AX:  -0.199 AY:   0.409 AZ:  10.003   |   GX:   0.005 GY:   0.002 GZ:   0.005

======================================================================================================================================

now im going to rite a single python script to do both works of serial_reader.py and phyphox_reader.py
paste teh following into app.py

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

=====================================================================================================================================================

after running python app.py i got:

========================================================================
                 DRONE IMU CALIBRATOR  V1
========================================================================

Axis             STM32           Phone      Difference
------------------------------------------------------------------------
AX              -0.685           0.723           1.408
AY               0.400          -0.335           0.735
AZ               9.977           9.888           0.089
GX               0.003          -0.001           0.004
GY              -0.000          -0.001           0.001
GZ               0.006          -0.001           0.007

Average Accelerometer Error : 0.7437 m/s²
Average Gyroscope Error     : 0.0041 rad/s

which is excellent the only thing is that i changed my signs in the drone which if ignoredrn is quite a good reading, in the future the software will auto correct it

========================================================================================================================================================

es it shoudl be flexible and when in teh gui o the screen its shows to move and rotate in a secific direction the software will automatically knowand will adjust accordingle ad will also show the user the negative signs if any so he may know, now lets move on to teh next step, teh GUI my favourite, as i told you i want yo to scan all local network on which the softwrae is running and when it matches teh one that llooks like a PhyPhox it shoudl automatically connect to it otherwise we may add a dialog box near the auto connect button to manually enter teh ip and i want a dark colourful not dark but a what is it called monolithic or what not which has boxes of different patterns and colours but good like GUI colours, lets make it

========================================================================================================================================================

now i am making a single python script taht merges everything , no app.py or serial_reader or phyphox reader jsut ne script not even any exteral assets,

after this i did used many ai platforms and created a single 1k+ lined py file that now works perfectly, i deleted every other file and now the folder has .venv and requirements.txt and DroneIMUCalibrator.py

im installing "pip install pyinstaller"

after this im building a single exe using "pyinstaller --onefile --windowed --name DroneIMUCalibrator --collect-all matplotlib --collect-all PyQt6 DroneIMUCalibrator.py"





