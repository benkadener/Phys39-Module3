// Part 2: First Manual Sketch - Fixed Direction

// ---------- Pins ----------
const int thermistorPin = A0;
const int potPin = A1;

const int pwmPin9 = 9;
const int pwmPin10 = 10;

// ---------- Thermistor constants ----------
const float Vref = 5.0;              // Arduino reference voltage
const float fixedResistance = 100.0; // fixed resistor in kOhm
const float R0 = 100.0;              // thermistor resistance at 25 C in kOhm
const float T0 = 298.15;             // 25 C in Kelvin
const float beta = 4540.0;           // thermistor beta value in K

const int numSamples = 1000;


// Average the thermistor ADC readings
float averageThermistorADC() {

  float totalADC = 0;

  for (int i = 0; i < numSamples; i++) {
    totalADC += analogRead(thermistorPin);
  }

  return totalADC / numSamples;
}


// Convert ADC value to voltage
float adcToVoltage(float averageADC) {

  return averageADC * Vref / 1023.0;
}


// Convert voltage to thermistor resistance
float voltageToResistance(float voltage) {

  return fixedResistance * voltage / (Vref - voltage);
}


// Convert thermistor resistance to Celsius
float resistanceToCelsius(float resistance) {

  float temperatureK =
      1.0 / ((1.0 / T0) +
      (1.0 / beta) * log(resistance / R0));

  return temperatureK - 273.15;
}


void setup() {

  Serial.begin(9600);

  pinMode(pwmPin9, OUTPUT);
  pinMode(pwmPin10, OUTPUT);

  // Start safely with PWM = 0
  analogWrite(pwmPin9, 0);
  analogWrite(pwmPin10, 0);
}


void loop() {

  // ----- Measure temperature -----

  float averageADC = averageThermistorADC();

  float voltage = adcToVoltage(averageADC);

  float resistance = voltageToResistance(voltage);

  float temperatureC = resistanceToCelsius(resistance);


  // ----- Read trim potentiometer -----

  int potADC = analogRead(potPin);

  // Convert 0-1023 ADC range to 0-255 PWM range
  int pwmCommand = map(potADC, 0, 1023, 0, 255);


  // ----- Fixed direction -----

  // Pin 9 must remain LOW
  analogWrite(pwmPin9, 0);

  // Pin 10 receives the PWM command
  analogWrite(pwmPin10, pwmCommand);


  // ----- Time -----

  float timeSeconds = millis() / 1000.0;


  // ----- Serial output -----

  Serial.print("Temperature (C): ");
  Serial.print(temperatureC, 2);

  Serial.print(", Time (s): ");
  Serial.print(timeSeconds, 2);

  Serial.print(", PWM: ");
  Serial.print(pwmCommand);

  Serial.print(", Active PWM pin: ");
  Serial.println(10);

}