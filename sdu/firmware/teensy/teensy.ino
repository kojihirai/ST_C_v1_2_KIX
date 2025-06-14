constexpr uint32_t BAUD = 6'000'000;
constexpr uint8_t  SYNC = 0xA5;
constexpr bool     USE_CHECKSUM = true;

constexpr uint8_t DRILL_PIN  = A6;
constexpr uint8_t POWER_PIN  = A7;
constexpr uint8_t LINEAR_PIN = A8;

struct __attribute__((packed)) Sample {
  uint16_t drill;
  uint16_t power;
  uint16_t linear;
};

static inline void sendSample(const Sample& s)
{
  if constexpr (USE_CHECKSUM) {
    uint8_t chk = 0;
    const uint8_t* p = reinterpret_cast<const uint8_t*>(&s);
    for (size_t i = 0; i < sizeof(Sample); ++i) chk ^= p[i];

    Serial.write(SYNC);
    Serial.write(p, sizeof(Sample));
    Serial.write(chk);
  } else {
    Serial.write(reinterpret_cast<const uint8_t*>(&s), sizeof(Sample));
  }
}

void setup()
{
  Serial.begin(BAUD);
  while (!Serial) ;

  analogReadResolution(12);
  analogReadAveraging(0);
}

void loop()
{
  Sample s;
  s.drill  = analogRead(DRILL_PIN);
  s.power  = analogRead(POWER_PIN);
  s.linear = analogRead(LINEAR_PIN);

  sendSample(s);
}
