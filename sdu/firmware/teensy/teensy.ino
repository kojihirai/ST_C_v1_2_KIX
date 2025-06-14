const int DRILL_CURRENT_PIN  = A6;
const int POWER_CURRENT_PIN  = A7;
const int LINEAR_CURRENT_PIN = A8;

const float VREF         = 3.3f;
const int   ADC_MAX      = 4095;
const float SENS_DRILL   = 0.1f; 
const float SENS_POWER   = 0.1f;
const float SENS_LINEAR  = 0.1875f;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogReadAveraging(4);
  while (!Serial);
}

void loop() {
  uint16_t rawDrill  = analogRead(DRILL_CURRENT_PIN);
  uint16_t rawPower  = analogRead(POWER_CURRENT_PIN);
  uint16_t rawLinear = analogRead(LINEAR_CURRENT_PIN);

  float voltDrill  = rawDrill  * VREF / ADC_MAX;
  float voltPower  = rawPower  * VREF / ADC_MAX;
  float voltLinear = rawLinear * VREF / ADC_MAX;

  float currDrill  = (voltDrill  * 1000.0f) / SENS_DRILL;
  float currPower  = (voltPower  * 1000.0f) / SENS_POWER;
  float currLinear = (voltLinear * 1000.0f) / SENS_LINEAR;

  Serial.print(currDrill,  2);
  Serial.print(',');
  Serial.print(currPower,  2);
  Serial.print(',');
  Serial.print(currLinear, 2);
  Serial.print('\n');
}