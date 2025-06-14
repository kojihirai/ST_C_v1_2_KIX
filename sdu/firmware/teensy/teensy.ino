const int DRILL_CURRENT_PIN  = A6;
const int POWER_CURRENT_PIN  = A7;
const int LINEAR_CURRENT_PIN = A8;

// ADC config
const int   VREF_uV   = 3300000;  // in microvolts
const int   ADC_MAX   = 4095;
const float AMP_SCALE = 100.0f;   // e.g. 3.45 A => 345

// Sensor sensitivities (in uV per A)
const int SENS_DRILL_uV  = 100000;   // 0.1 V/A
const int SENS_POWER_uV  = 100000;
const int SENS_LINEAR_uV = 187500;   // 0.1875 V/A

// Precomputed scaling factors (in micro-units)
const int32_t SCALE_DRILL  = (int32_t)VREF_uV * AMP_SCALE / (ADC_MAX * SENS_DRILL_uV);
const int32_t SCALE_POWER  = (int32_t)VREF_uV * AMP_SCALE / (ADC_MAX * SENS_POWER_uV);
const int32_t SCALE_LINEAR = (int32_t)VREF_uV * AMP_SCALE / (ADC_MAX * SENS_LINEAR_uV);

void setup() {
  analogReadResolution(12);
  analogReadAveraging(0);
  Serial.begin(2000000);
  while (!Serial);
}

void loop() {
  uint16_t raw_drill  = analogRead(DRILL_CURRENT_PIN);
  uint16_t raw_power  = analogRead(POWER_CURRENT_PIN);
  uint16_t raw_linear = analogRead(LINEAR_CURRENT_PIN);

  int16_t drill_amp  = raw_drill  * SCALE_DRILL;
  int16_t power_amp  = raw_power  * SCALE_POWER;
  int16_t linear_amp = raw_linear * SCALE_LINEAR;

  // Send all three values in one go (6 bytes total)
  Serial.write((uint8_t*)&drill_amp, sizeof(int16_t));
  Serial.write((uint8_t*)&power_amp, sizeof(int16_t));
  Serial.write((uint8_t*)&linear_amp, sizeof(int16_t));
}
