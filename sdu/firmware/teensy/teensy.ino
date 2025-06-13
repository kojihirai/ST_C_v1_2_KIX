
const int DRILL_CURRENT_PIN  = A6;
const int POWER_CURRENT_PIN  = A7;
const int LINEAR_CURRENT_PIN = A8;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogReadAveraging(4);
  while (!Serial);
}

void loop() {
  int drill  = analogRead(DRILL_CURRENT_PIN);
  int power  = analogRead(POWER_CURRENT_PIN);
  int linear = analogRead(LINEAR_CURRENT_PIN);

  Serial.print(drill);
  Serial.print(',');
  Serial.print(power);
  Serial.print(',');
  Serial.print(linear);
  Serial.print('\n');
}
