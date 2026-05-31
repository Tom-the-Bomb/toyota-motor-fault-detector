/*
 * Example Arduino sketch: prints motor telemetry the backend understands.
 *
 * The backend's parser accepts THREE formats — pick whichever is easiest:
 *   1) CSV  (lightest):   current,voltage,temperature,rpm,torque,load,vibration
 *   2) JSON:              {"current":1.23,"temperature":45.6,...}
 *   3) key=value:         current=1.23 temperature=45.6 ...
 *
 * The column order for CSV must match config.CSV_FIELDS in the backend:
 *   current, voltage, temperature, rpm, torque, load, vibration
 *
 * Replace the analogRead()/placeholder math below with your real sensors
 * (e.g. ACS712 current sensor, thermistor, hall-effect tachometer, etc.).
 *
 * Baud rate must match config.BAUD_RATE (default 115200).
 */

void setup() {
  Serial.begin(115200);
}

void loop() {
  // --- Read your real sensors here -----------------------------------------
  float current     = readCurrent();        // Amps   (e.g. ACS712 on A0)
  float voltage     = 12.0;                  // Volts  (measured or fixed)
  float temperature = readTemperature();     // °C     (thermistor on A1)
  float rpm         = readRPM();             // RPM    (hall sensor / encoder)
  float torque      = current * 0.5;         // N·m    (estimate or sensor)
  float load        = (current / 6.0) * 100; // %      (current as % of stall)
  float vibration   = readVibration();       // g      (accelerometer)

  // --- Print one CSV line per sample ---------------------------------------
  Serial.print(current);     Serial.print(',');
  Serial.print(voltage);     Serial.print(',');
  Serial.print(temperature); Serial.print(',');
  Serial.print(rpm);         Serial.print(',');
  Serial.print(torque);      Serial.print(',');
  Serial.print(load);        Serial.print(',');
  Serial.println(vibration);

  delay(50); // ~20 samples/sec
}

// ---- Replace these stubs with your actual sensor reads ----------------------
float readCurrent()     { return analogRead(A0) * (5.0 / 1023.0); }
float readTemperature() { return 25.0 + analogRead(A1) * 0.05; }
float readRPM()         { return 1500.0; }
float readVibration()   { return 0.25; }
