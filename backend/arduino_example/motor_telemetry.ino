/*
 * Example Arduino sketch: prints DIRECTLY-MEASURED motor telemetry.
 *
 * We only send what we can actually measure off the motor wires with an
 * INA219 current/voltage sensor (I2C): current (A) and bus voltage (V).
 * No estimated values (torque, load) and no add-on transducers (temp, rpm).
 *
 * The backend's parser accepts any of these — pick the easiest:
 *   1) CSV  (lightest):   current,voltage     e.g.  1.23,12.04
 *   2) JSON:              {"current":1.23,"voltage":12.04}
 *
 * The CSV column order must match config.CSV_FIELDS in the backend:
 *   current, voltage
 *
 * Wiring (INA219 breakout):
 *   INA219 VCC -> 5V,  GND -> GND,  SDA -> A4,  SCL -> A5  (Uno/Nano)
 *   Motor supply current flows through the INA219 Vin+ / Vin- terminals.
 *
 * Library: "Adafruit INA219" (install via Arduino Library Manager).
 * Baud rate must match config.BAUD_RATE (default 115200).
 */

#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;

void setup() {
  Serial.begin(115200);
  ina219.begin();          // defaults to 0x40
}

void loop() {
  float current = ina219.getCurrent_mA() / 1000.0;  // A
  float voltage = ina219.getBusVoltage_V();          // V

  // One CSV line per sample: current,voltage
  Serial.print(current, 3);
  Serial.print(',');
  Serial.println(voltage, 3);

  delay(50); // ~20 samples/sec
}
