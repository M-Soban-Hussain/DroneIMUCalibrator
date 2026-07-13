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