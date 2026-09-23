"""Display Arduino temperature measurements in a rolling strip chart."""

import csv
import re
import sys
from collections import deque

import pyqtgraph as pg
import serial
from PySide6 import QtCore, QtGui, QtWidgets


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
	"""Read Arduino measurements and provide manual serial controls."""

	def __init__(self):
		super().__init__()
		self.setWindowTitle("TEC Temperature")

		# Keep the rolling chart data separate from the CSV output values.
		self.times = deque()
		self.temperatures = deque()
		self.heat_times = deque()
		self.heat_pwms = deque()
		self.cool_times = deque()
		self.cool_pwms = deque()
		self.serial_buffer = b""

		# Create the manual controls and the live values shown above the plots.
		controls = QtWidgets.QGroupBox("Manual controls")
		controls_layout = QtWidgets.QGridLayout(controls)

		self.direction_switch = QtWidgets.QCheckBox("HEAT")
		self.direction_switch.setChecked(True)
		self.direction_switch.toggled.connect(self.direction_changed)
		controls_layout.addWidget(QtWidgets.QLabel("Direction"), 0, 0)
		controls_layout.addWidget(self.direction_switch, 0, 1)

		self.pwm_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
		self.pwm_slider.setRange(0, 255)
		self.pwm_slider.setValue(0)
		self.pwm_slider.valueChanged.connect(self.slider_changed)
		controls_layout.addWidget(QtWidgets.QLabel("PWM"), 1, 0)
		controls_layout.addWidget(self.pwm_slider, 1, 1)

		self.pwm_input = QtWidgets.QLineEdit("0")
		self.pwm_input.setValidator(QtGui.QIntValidator(0, 255, self))
		self.pwm_input.setMaximumWidth(80)
		self.pwm_input.editingFinished.connect(self.text_pwm_changed)
		controls_layout.addWidget(self.pwm_input, 1, 2)

		self.temperature_value = QtWidgets.QLabel("-- C")
		self.pwm_value = QtWidgets.QLabel("--")
		self.direction_value = QtWidgets.QLabel("--")
		self.time_value = QtWidgets.QLabel("-- s")
		live_values = QtWidgets.QFormLayout()
		live_values.addRow("Temperature", self.temperature_value)
		live_values.addRow("PWM", self.pwm_value)
		live_values.addRow("Direction", self.direction_value)
		live_values.addRow("Elapsed time", self.time_value)
		controls_layout.addLayout(live_values, 0, 3, 2, 1)

		# The first plot displays the measured temperature over Arduino time.
		self.temperature_plot = pg.PlotWidget()
		self.temperature_plot.setLabel("bottom", "Time", units="s")
		self.temperature_plot.setLabel("left", "Temperature", units="C")
		self.temperature_plot.setYRange(TEMPERATURE_MIN_C, TEMPERATURE_MAX_C)
		self.temperature_plot.showGrid(x=True, y=True, alpha=0.25)
		self.temperature_curve = self.temperature_plot.plot(
			pen=pg.mkPen("#d95f02", width=2)
		)

		# The second plot keeps separate solid curves for heating and cooling.
		self.pwm_plot = pg.PlotWidget()
		self.pwm_plot.setLabel("bottom", "Time", units="s")
		self.pwm_plot.setLabel("left", "PWM")
		self.pwm_plot.setYRange(0, 255)
		self.pwm_plot.showGrid(x=True, y=True, alpha=0.25)
		self.heat_curve = self.pwm_plot.plot(pen=pg.mkPen("r", width=2))
		self.cool_curve = self.pwm_plot.plot(pen=pg.mkPen("b", width=2))

		central_widget = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout(central_widget)
		layout.addWidget(controls)
		layout.addWidget(self.temperature_plot)
		layout.addWidget(self.pwm_plot)
		self.setCentralWidget(central_widget)

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

	def set_pwm_value(self, pwm):
		"""Keep the slider and text box synchronized at a valid PWM value."""
		pwm = max(0, min(255, pwm))
		self.pwm_slider.blockSignals(True)
		self.pwm_input.blockSignals(True)
		self.pwm_slider.setValue(pwm)
		self.pwm_input.setText(str(pwm))
		self.pwm_slider.blockSignals(False)
		self.pwm_input.blockSignals(False)
		return pwm

	def send_control_command(self, pwm):
		"""Send one manual control command to the Arduino."""
		direction = "HEAT" if self.direction_switch.isChecked() else "COOL"
		command = f"SET PWM {pwm} DIR {direction}\n"
		self.serial_port.write(command.encode("ascii"))

	def slider_changed(self, pwm):
		"""Send a command when the user moves the PWM slider."""
		pwm = self.set_pwm_value(pwm)
		self.send_control_command(pwm)

	def text_pwm_changed(self):
		"""Clamp typed PWM input and send the resulting command."""
		try:
			pwm = int(self.pwm_input.text())
		except ValueError:
			pwm = 0
		pwm = self.set_pwm_value(pwm)
		self.send_control_command(pwm)

	def direction_changed(self, heating):
		"""Send the current PWM with the newly selected direction."""
		self.direction_switch.setText("HEAT" if heating else "COOL")
		self.send_control_command(self.pwm_slider.value())

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
			if heat_cool:
				self.heat_times.append(time_seconds)
				self.heat_pwms.append(pwm)
			else:
				self.cool_times.append(time_seconds)
				self.cool_pwms.append(pwm)

			self.temperature_value.setText(f"{temperature:.2f} C")
			self.pwm_value.setText(str(pwm))
			self.direction_value.setText("HEAT" if heat_cool else "COOL")
			self.time_value.setText(f"{time_seconds:.2f} s")
			oldest_time = time_seconds - WINDOW_DURATION_SECONDS
			while self.times and self.times[0] < oldest_time:
				self.times.popleft()
				self.temperatures.popleft()
			while self.heat_times and self.heat_times[0] < oldest_time:
				self.heat_times.popleft()
				self.heat_pwms.popleft()
			while self.cool_times and self.cool_times[0] < oldest_time:
				self.cool_times.popleft()
				self.cool_pwms.popleft()

		# Refresh both plots after processing the available serial data.
		self.temperature_curve.setData(list(self.times), list(self.temperatures))
		self.heat_curve.setData(list(self.heat_times), list(self.heat_pwms))
		self.cool_curve.setData(list(self.cool_times), list(self.cool_pwms))

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
