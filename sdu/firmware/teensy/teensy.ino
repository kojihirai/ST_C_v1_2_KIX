const int DRILL_PIN  = A6;
const int POWER_PIN  = A7;
const int LINEAR_PIN = A8;

constexpr int   ADC_MAX      = 4095;
constexpr float VREF         = 3.3f;
constexpr float SCALE_FACTOR = 100.0f;

constexpr int SENS_DRILL_uV  = 100000;
constexpr int SENS_POWER_uV  = 100000;
constexpr int SENS_LINEAR_uV = 187500;

constexpr int32_t VREF_uV    = 3300000;
constexpr int32_t MUL_DRILL  = (VREF_uV * SCALE_FACTOR) / (ADC_MAX * SENS_DRILL_uV);
constexpr int32_t MUL_POWER  = (VREF_uV * SCALE_FACTOR) / (ADC_MAX * SENS_POWER_uV);
constexpr int32_t MUL_LINEAR = (VREF_uV * SCALE_FACTOR) / (ADC_MAX * SENS_LINEAR_uV);

constexpr uint8_t SYNC_BYTE = '\n';

void setup() {
  analogReadResolution(12);
  analogReadAveraging(0);
  Serial.begin(6000000);
  while (!Serial);
}

void loop() {
  uint16_t rawDrill  = analogRead(DRILL_PIN);
  uint16_t rawPower  = analogRead(POWER_PIN);
  uint16_t rawLinear = analogRead(LINEAR_PIN);

  int16_t sDrill  = int16_t(rawDrill  * MUL_DRILL);
  int16_t sPower  = int16_t(rawPower  * MUL_POWER);
  int16_t sLinear = int16_t(rawLinear * MUL_LINEAR);

  Serial.write((uint8_t*)&sDrill, sizeof(sDrill));
  Serial.write((uint8_t*)&sPower, sizeof(sPower));
  Serial.write((uint8_t*)&sLinear, sizeof(sLinear));
  Serial.write(SYNC_BYTE);
}
