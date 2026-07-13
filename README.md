# Drone IMU Calibrator

A Python-based GUI application for calibrating IMU sensors by comparing measurements from an STM32 microcontroller with reference data collected using the Phyphox mobile application.

## Features

- GUI built with PyQt6
- Reads IMU data from STM32 over USB serial
- Reads reference sensor data from Phyphox over Wi-Fi
- Calculates accelerometer calibration parameters
- Supports real-time data visualization

## Requirements

- Python 3.11+
- Windows
- STM32 board
- Phyphox app

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python DroneIMUCalibrator.py
```

## Build Executable

To create a standalone executable:

```bash
pyinstaller --onefile --windowed DroneIMUCalibrator.py
```

The executable will be generated inside the `dist` folder.

## Project Structure

```
DroneIMUCalibrator/
│
├── DroneIMUCalibrator.py
├── CalibrationProfile.json
├── requirements.txt
├── README.md
└── assets/ (optional)
```

## Output

Calibration results are stored in:

```
CalibrationProfile.json
```

## License

This project is intended for educational and research purposes.
