# Phys 39/169 Instrumentation Project

**Team members:** Benjamin Kadener and Kian Wijnaendts

**Repository URL:** [Phys39-Module 3](https://github.com/benkadener/Phys39-Module3)

## Project Purpose

This project measures the temperature of a thermoelectric cooler (TEC), applies manual open-loop heating or cooling power through a H-bridge, and displays the measurements in Python. It addresses how thermistor temperature changes when PWM power and TEC direction are changed. It does not automatically regulate the TEC to a target temperature.

## Current Working Configuration

The current GUI configuration uses the Part 6 Arduino sketch:

`Part 6/Arduino_TEC_GUI.ino/Arduino_TEC_GUI.ino.ino`

It accepts Python commands in addition to supporting the manual potentiometer and direction switch before serial control is enabled. The paired Python program is:

`Part 4/tec_temperature_strip_chart.py`

The Python program reads and plots the Arduino measurement format, prints accepted measurements, saves CSV data, and sends GUI commands. The Part 3 sketch remains available as the hardware-only manual version.

## Hardware And Pin Assignments

| Function | Arduino pin or connection | Notes |
| --- | --- | --- |
| Thermistor divider | `A0` | Temperature measurement |
| Trim potentiometer | `A1` | Manual PWM command from `0` to `255` |
| H-bridge heat/cool input | `9` | PWM output for one direction |
| H-bridge heat/cool input | `10` | PWM output for the other direction |
| Direction switch center | `11` | SPDT switch common terminal |
| Direction switch outer terminals | `5V` and `GND` | Selects the direction input |
| H-bridge ground | Arduino `GND` | Shared signal reference |
| TEC power path | H-bridge, TEC, and normally closed thermal switch | High-current actuator circuit |



## How To Run The Instrument

1. Confirm that the thermistor, potentiometer, direction switch, H-bridge, TEC, normally closed thermal switch, pump, and fans are connected correctly. Confirm that the Arduino and H-bridge share ground.
2. Confirm that the heat-exchanger pump and radiator fans are operating. Confirm the thermal cutoff and current limit, and obtain instructor approval before applying TEC power.
3. Upload `Part 2/tec_manual_fixed_direction/tec_manual_fixed_direction.ino` for the first fixed-direction test, `Part 3/tec_manual_hardware_direction/tec_manual_hardware_direction.ino` for manual direction control, or `Part 6/Arduino_TEC_GUI.ino/Arduino_TEC_GUI.ino.ino` for the Python GUI.
4. Open Serial Monitor at `9600` baud and verify the measurement lines. Close Serial Monitor completely before running Python because the USB serial connection cannot be shared.
5. In `Part 4/tec_temperature_strip_chart.py`, set `SERIAL_PORT`, `BAUD_RATE`, plot limits, and `CSV_FILENAME` near the top of the file.
6. Install `pyserial`, `PySide6`, and `pyqtgraph`, then run:

	```bash
	python3 "Part 4/tec_temperature_strip_chart.py"
	```

The Arduino measurement format is:

```text
Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1
```

`Temperature (C)` is the thermistor temperature, `Time (s)` is elapsed Arduino time, `PWM` is the manual command from `0` to `255`, and `Heat/Cool` is the observed direction, where `1` means heating and `0` means cooling. In the current Part 3 calibration, pin `11 = LOW` selects pin `10` and reports heating; pin `11 = HIGH` selects pin `9` and reports cooling.

The Python program reads serial data in `read_measurements()`, parses each line with `parse_measurement()`, prints the accepted fields, writes rows to `temperature_measurements.csv`, and updates the temperature and PWM plots. The GUI command function `send_control_command()` sends commands such as `SET PWM 120 DIR HEAT`; the Part 6 Arduino sketch parses these commands. The Part 3 sketch does not parse them.

## Repository Map

- `Part 2/tec_manual_fixed_direction/`: first manual fixed-direction Arduino sketch.
- `Part 3/tec_manual_hardware_direction/`: second manual Arduino sketch with the physical direction switch.
- `Part 4/`: Python strip-chart program and temperature CSV data.
- `part 5/`: additional temperature CSV data.
- `Part 6/Arduino_TEC_GUI.ino/`: Arduino sketch paired with the Python GUI.
- `Part 7/`: integrated test evidence and workspace material.

## Current Results

The manual sketches and the Part 6 GUI sketch average `1000` thermistor ADC measurements, start with both PWM outputs off, and report temperature, time, PWM, and observed heat/cool direction. The Part 3 sketch is the hardware-only version without GUI controls.

The oscilloscope observations were recorded with `0.5 ms/div` horizontally and `5 V/div` vertically. The PWM period is approximately four horizontal divisions:

$$
T \approx 4(0.5\ \mathrm{ms}) = 2.0\ \mathrm{ms},\qquad
f \approx \frac{1}{T} = 500\ \mathrm{Hz}
$$

The active pulse is approximately one division of a four-division period, so the duty cycle is approximately `25%`. The opposite H-bridge output is complementary at approximately `75%`.

| Pin `11` input | Pin `9` waveform | Pin `10` waveform | `M+` waveform | `M-` waveform | PWM frequency | PWM duty cycle |
| --- | --- | --- | --- | --- | --- | --- |
| `5 V` | PWM signal | Approximately `0 V` | Complementary H-bridge PWM | H-bridge PWM | Approximately `500 Hz` | Approximately `25%` active pulse, `75%` complementary |
| `0 V` | Approximately `0 V` | PWM signal | H-bridge PWM | Complementary H-bridge PWM | Approximately `500 Hz` | Approximately `75%` active pulse, `25%` complementary |

The H-bridge output photograph is [Oscilloscope_M+_M-.jpeg](Part%203/Oscilloscope_M%2B_M-.jpeg). The H-bridge photograph shows the `M+` and `M-` outputs switching in opposite phases, confirming that changing the direction reverses the corresponding output behavior. The vertical scale is `5 V/div`, so the logic-level traces are approximately `0 V` to `5 V`.

The heating and cooling serial records are [Serial_Monitor_heating.png](Part%203/Serial_Monitor_heating.png) and [Serial_Monitor_Cooling.png](Part%203/Serial_Monitor_Cooling.png). The serial interface record is [Serial_Monitor_Serial_Interface.png](Part%203/Serial_Monitor_Serial_Interface.png).


## Known Problems And What we dont understand

- Our Power Supply exploded :(
- Had trouble with oscilloscope in the beggining but fixed it

## AI Use Note

AI helped generate and revise portions of the Arduino sketches, the Python serial parser, the GUI controls, and some of this README. We modified the code to match the actual pin assignments, observed heat/cool mapping, assignment serial format, and files in this repository. We tested the Arduino source structure and serial formatting through local checks, and ran the Python program locally. Hardware behavior, oscilloscope measurements, wiring safety, and heating/cooling labels must be verified on the actual apparatus.