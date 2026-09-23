"""Display Arduino temperature measurements in a rolling strip chart."""

import csv
import re
import sys
from collections import deque

import pyqtgraph as pg
import serial
from PySide6 import QtCore, QtWidgets


# ---------- Settings to change before running ----------
SERIAL_PORT = "/dev/cu.usbmodem101"
BAUD_RATE = 9600
WINDOW_DURATION_SECONDS = 120.0
UPDATE_INTERVAL_MILLISECONDS = 100
TEMPERATURE_MIN_C = 0.0
TEMPERATURE_MAX_C = 50.0
CSV_FILENAME = "temperature_measurements.csv"


# This matches the serial line printed by the Part 3 Arduino sketch.
MEASUREMENT_LINE = re.compile(
	r"^Temperature \(C\):\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)),\s*"
	r"Time \(s\):\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)),\s*"
	r"PWM:\s*(\d+),\s*Heat/Cool:\s*([01])\s*$"
)


def parse_measurement(line):
	"""Return time, temperature, PWM, and direction, or None if malformed."""
	match = MEASUREMENT_LINE.fullmatch(line.strip())
	if match is None:
		return None

	temperature = float(match.group(1))
	time_seconds = float(match.group(2))
	pwm = int(match.group(3))
	heat_cool = int(match.group(4))

	return time_seconds, temperature, pwm, heat_cool


class TemperatureWindow(QtWidgets.QMainWindow):
	"""Read measurements and show only temperature against Arduino time."""

	def __init__(self):
		super().__init__()
		self.setWindowTitle("TEC Temperature")

		# Keep the rolling chart data separate from the CSV output values.
		self.times = deque()
		self.temperatures = deque()
		self.serial_buffer = b""

		self.plot = pg.PlotWidget()
		self.plot.setLabel("bottom", "Time", units="s")
		self.plot.setLabel("left", "Temperature", units="C")
		self.plot.setYRange(TEMPERATURE_MIN_C, TEMPERATURE_MAX_C)
		self.plot.showGrid(x=True, y=True, alpha=0.25)
		self.temperature_curve = self.plot.plot(pen=pg.mkPen("#d95f02", width=2))
		self.setCentralWidget(self.plot)

		# Open the serial port for reading only. No commands are sent.
		self.serial_port = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
		self.csv_file = open(CSV_FILENAME, "a", newline="")
		self.csv_writer = csv.writer(self.csv_file)
		if self.csv_file.tell() == 0:
			self.csv_writer.writerow(
				["time_s", "temperature_C", "pwm", "heat_cool"]
			)
			self.csv_file.flush()

		self.timer = QtCore.QTimer(self)
		self.timer.timeout.connect(self.read_measurements)
		self.timer.start(UPDATE_INTERVAL_MILLISECONDS)

	def read_measurements(self):
		"""Read all currently available lines and process valid ones."""
		if self.serial_port.in_waiting:
			self.serial_buffer += self.serial_port.read(self.serial_port.in_waiting)

		while b"\n" in self.serial_buffer:
			raw_line, self.serial_buffer = self.serial_buffer.split(b"\n", 1)
			line = raw_line.decode("ascii", errors="ignore")
			measurement = parse_measurement(line)
			if measurement is None:
				continue

			time_seconds, temperature, pwm, heat_cool = measurement
			print(
				f"Temperature (C): {temperature:.2f}, "
				f"Time (s): {time_seconds:.2f}, PWM: {pwm}, "
				f"Heat/Cool: {heat_cool}"
			)
			self.csv_writer.writerow(
				[time_seconds, temperature, pwm, heat_cool]
			)
			self.csv_file.flush()

			self.times.append(time_seconds)
			self.temperatures.append(temperature)
			oldest_time = time_seconds - WINDOW_DURATION_SECONDS
			while self.times and self.times[0] < oldest_time:
				self.times.popleft()
				self.temperatures.popleft()

		self.temperature_curve.setData(list(self.times), list(self.temperatures))

	def closeEvent(self, event):
		"""Close files and the serial connection with the application."""
		self.timer.stop()
		self.serial_port.close()
		self.csv_file.close()
		event.accept()


def main():
	"""Start the display application."""
	application = QtWidgets.QApplication(sys.argv)
	window = TemperatureWindow()
	window.resize(900, 500)
	window.show()
	sys.exit(application.exec())


if __name__ == "__main__":
	main()
