// Part 3: Second Manual Sketch - Hardware Direction Input

#include <stdio.h>
#include <string.h>

// ---------- Pins ----------
const int thermistorPin = A0;
const int potPin = A1;

const int pwmPin9 = 9;
const int pwmPin10 = 10;
const int directionPin = 11;

// ---------- Thermistor constants ----------
const float Vref = 5.0;
const float fixedResistance = 100.0; // kOhm
const float R0 = 100.0;              // kOhm at 25 C
const float T0 = 298.15;             // 25 C in Kelvin
const float beta = 4540.0;           // K

const int numSamples = 1000;

// These values are updated by the hardware controls or the Python GUI.
int pwmCommand = 0;
int direction = LOW;
bool serialControl = false;
char commandBuffer[40];
int commandLength = 0;


// Read commands sent by the Python strip-chart interface.
void readSerialCommands() {

  while (Serial.available() > 0) {

    char incomingCharacter = Serial.read();

    if (incomingCharacter == '\n' || incomingCharacter == '\r') {

      if (commandLength == 0) {
        continue;
      }

      commandBuffer[commandLength] = '\0';

      int requestedPWM;
      char requestedDirection[5];

      int valuesRead = sscanf(
          commandBuffer,
          "SET PWM %d DIR %4s",
          &requestedPWM,
          requestedDirection
      );

      if (valuesRead == 2 && requestedPWM >= 0 && requestedPWM <= 255) {

        if (strcmp(requestedDirection, "HEAT") == 0) {
          direction = LOW;
        } else if (strcmp(requestedDirection, "COOL") == 0) {
          direction = HIGH;
        } else {
          commandLength = 0;
          continue;
        }

        pwmCommand = requestedPWM;
        serialControl = true;
      }

      commandLength = 0;

    } else if (commandLength < sizeof(commandBuffer) - 1) {
      commandBuffer[commandLength] = incomingCharacter;
      commandLength++;
    }
  }
}


// Average thermistor ADC readings
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
  pinMode(directionPin, INPUT);

  // Safe startup: both PWM outputs OFF
  analogWrite(pwmPin9, 0);
  analogWrite(pwmPin10, 0);
}


void loop() {

  // The GUI can take control by sending a complete command line.
  readSerialCommands();

  // ---------- Measure temperature ----------

  float averageADC = averageThermistorADC();

  float voltage = adcToVoltage(averageADC);

  float resistance = voltageToResistance(voltage);

  float temperatureC = resistanceToCelsius(resistance);


  // ---------- Read potentiometer ----------

  if (!serialControl) {
    int potADC = analogRead(potPin);
    pwmCommand = map(potADC, 0, 1023, 0, 255);
    direction = digitalRead(directionPin);
  }

  int activePin;


  // ---------- Select PWM direction ----------

  if (direction == HIGH) {

    // Pin 11 = 5 V
    // Pin 9 gets PWM, pin 10 stays LOW
    analogWrite(pwmPin9, pwmCommand);
    analogWrite(pwmPin10, 0);

    activePin = 9;

  } else {

    // Pin 11 = 0 V
    // Pin 9 stays LOW, pin 10 gets PWM
    analogWrite(pwmPin9, 0);
    analogWrite(pwmPin10, pwmCommand);

    activePin = 10;
  }


  // ---------- Time ----------

  float timeSeconds = millis() / 1000.0;


  // ---------- Serial output ----------

  Serial.print("Temperature (C): ");
  Serial.print(temperatureC, 2);

  Serial.print(", Time (s): ");
  Serial.print(timeSeconds, 2);

  Serial.print(", PWM: ");
  Serial.print(pwmCommand);

Serial.print(", Heat/Cool: ");

if (direction == LOW) {
  Serial.println(1);   // experimentally observed heating
} else {
  Serial.println(0);   // experimentally observed cooling
}
}