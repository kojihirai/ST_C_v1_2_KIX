const int DRILL_CURRENT_PIN  = A6;
const int POWER_CURRENT_PIN  = A7;
const int LINEAR_CURRENT_PIN = A8;

const int   VREF_uV   = 3300000;
const int   ADC_MAX   = 4095;
const float AMP_SCALE = 100.0f;

const int SENS_DRILL_uV  = 100000;
const int SENS_POWER_uV  = 100000;
const int SENS_LINEAR_uV = 187500;

const int32_t SCALE_DRILL  = (int32_t)VREF_uV * AMP_SCALE / (ADC_MAX * SENS_DRILL_uV);
const int32_t SCALE_POWER  = (int32_t)VREF_uV * AMP_SCALE / (ADC_MAX * SENS_POWER_uV);
const int32_t SCALE_LINEAR = (int32_t)VREF_uV * AMP_SCALE / (ADC_MAX * SENS_LINEAR_uV);

const uint8_t SYNC_BYTE = 0xAA;
const int BATCH_SIZE = 4;

int16_t buffer[BATCH_SIZE][3];  // 3 channels: drill, power, linear

void setup() {
  analogReadResolution(12);
  analogReadAveraging(0);
  Serial.begin(2000000);
  while (!Serial);
}

void loop() {
  for (int i = 0; i < BATCH_SIZE; i++) {
    uint16_t raw_drill  = analogRead(DRILL_CURRENT_PIN);
    uint16_t raw_power  = analogRead(POWER_CURRENT_PIN);
    uint16_t raw_linear = analogRead(LINEAR_CURRENT_PIN);

    buffer[i][0] = raw_drill  * SCALE_DRILL;
    buffer[i][1] = raw_power  * SCALE_POWER;
    buffer[i][2] = raw_linear * SCALE_LINEAR;
  }

  Serial.write(SYNC_BYTE);
  Serial.write((uint8_t*)buffer, sizeof(buffer));
}
