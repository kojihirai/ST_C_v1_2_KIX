const int DRILL_CURRENT_PIN  = A6;
const int POWER_CURRENT_PIN  = A7;
const int LINEAR_CURRENT_PIN = A8;

const float VREF         = 3.3f;
const int   ADC_MAX      = 4095;
const float SENS_DRILL   = 0.1f; 
const float SENS_POWER   = 0.1f;
const float SENS_LINEAR  = 0.1875f;

const float ADC_TO_VOLT = VREF / ADC_MAX;
const float DRILL_TO_AMP = ADC_TO_VOLT / SENS_DRILL;
const float POWER_TO_AMP = ADC_TO_VOLT / SENS_POWER;
const float LINEAR_TO_AMP = ADC_TO_VOLT / SENS_LINEAR;

void setup() {
  Serial.begin(2000000);
  analogReadResolution(12);
  analogReadAveraging(0);
  while (!Serial);
}

void loop() {
  uint16_t rawDrill  = analogRead(DRILL_CURRENT_PIN);
  uint16_t rawPower  = analogRead(POWER_CURRENT_PIN);
  uint16_t rawLinear = analogRead(LINEAR_CURRENT_PIN);

  float currDrill  = rawDrill * DRILL_TO_AMP;
  float currPower  = rawPower * POWER_TO_AMP;
  float currLinear = rawLinear * LINEAR_TO_AMP;

  Serial.print(currDrill, 2);
  Serial.write(',');
  Serial.print(currPower, 2);
  Serial.write(',');
  Serial.print(currLinear, 2);
  Serial.write('\n');
}