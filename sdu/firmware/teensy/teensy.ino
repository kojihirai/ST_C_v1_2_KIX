const int DRILL_CURRENT_PIN  = A6;
const int POWER_CURRENT_PIN  = A7;
const int LINEAR_CURRENT_PIN = A8;

// ADC config
const float VREF    = 3.3f;
const int   ADC_MAX = 4095;
const float ADC_TO_VOLT = VREF / ADC_MAX;

// Sensor sensitivities (V/A)
const float SENS_DRILL  = 0.1f;
const float SENS_POWER  = 0.1f;
const float SENS_LINEAR = 0.1875f;

// Output scaling
const float AMP_SCALE = 100.0f;  // 0.01 A resolution

// === Precomputed int16 scaling factors ===
const float SCALE_DRILL  = ADC_TO_VOLT / SENS_DRILL  * AMP_SCALE;
const float SCALE_POWER  = ADC_TO_VOLT / SENS_POWER  * AMP_SCALE;
const float SCALE_LINEAR = ADC_TO_VOLT / SENS_LINEAR * AMP_SCALE;

void setup() {
  Serial.begin(2000000);
  analogReadResolution(12);
  analogReadAveraging(0);
  while (!Serial);
}

inline void send_scaled(int pin, float scale) {
  int16_t value = analogRead(pin) * scale;
  Serial.write((uint8_t*)&value, sizeof(int16_t));
}

void loop() {
  send_scaled(DRILL_CURRENT_PIN,  SCALE_DRILL);
  send_scaled(POWER_CURRENT_PIN,  SCALE_POWER);
  send_scaled(LINEAR_CURRENT_PIN, SCALE_LINEAR);
}
