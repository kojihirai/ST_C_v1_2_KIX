#include <string.h>  // for memcpy

const int DRILL_PIN  = A6;
const int POWER_PIN  = A7;
const int LINEAR_PIN = A8;

constexpr float VREF         = 3.3f;
constexpr int   ADC_MAX      = 4095;
constexpr float SENS_DRILL   = 0.1f;
constexpr float SENS_POWER   = 0.1f;
constexpr float SENS_LINEAR  = 0.1875f;
constexpr float SCALE_FACTOR = 100.0f;

constexpr float MULT_DRILL  = VREF / ADC_MAX / SENS_DRILL  * SCALE_FACTOR;
constexpr float MULT_POWER  = VREF / ADC_MAX / SENS_POWER  * SCALE_FACTOR;
constexpr float MULT_LINEAR = VREF / ADC_MAX / SENS_LINEAR * SCALE_FACTOR;

constexpr size_t PACKET_SIZE   = 3 * sizeof(int16_t) + 1;
constexpr uint8_t SYNC_BYTE    = '\n';
constexpr uint8_t OFF_DRILL    = 0;
constexpr uint8_t OFF_POWER    = OFF_DRILL  + sizeof(int16_t);
constexpr uint8_t OFF_LINEAR   = OFF_POWER  + sizeof(int16_t);
constexpr uint8_t OFF_SYNC     = OFF_LINEAR + sizeof(int16_t);

void setup() {
  Serial.begin(2000000);
  analogReadResolution(12);
  analogReadAveraging(0);
  while (!Serial); 
}

void loop() {
  uint16_t rawDrill  = analogRead(DRILL_PIN);
  uint16_t rawPower  = analogRead(POWER_PIN);
  uint16_t rawLinear = analogRead(LINEAR_PIN);

  int16_t sDrill  = int16_t(rawDrill  * MULT_DRILL);
  int16_t sPower  = int16_t(rawPower  * MULT_POWER);
  int16_t sLinear = int16_t(rawLinear * MULT_LINEAR);

  uint8_t buf[PACKET_SIZE];
  memcpy(buf + OFF_DRILL,  &sDrill,  sizeof(sDrill));
  memcpy(buf + OFF_POWER,  &sPower,  sizeof(sPower));
  memcpy(buf + OFF_LINEAR, &sLinear, sizeof(sLinear));
  buf[OFF_SYNC] = SYNC_BYTE;
  Serial.write(buf, PACKET_SIZE);

}
