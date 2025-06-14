#include <ADC.h>
#include <DMAChannel.h>

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

ADC *adc = new ADC();
DMAChannel dma1;

const int BUFFER_SIZE = 100;  // Reduced buffer size for faster processing
uint16_t drillBuffer[BUFFER_SIZE];
uint16_t powerBuffer[BUFFER_SIZE];
uint16_t linearBuffer[BUFFER_SIZE];
volatile int bufferIndex = 0;
volatile bool newData = false;

void dma1_isr() {
  dma1.clearInterrupt();
  newData = true;
}

void setup() {
  Serial.begin(2000000);
  
  // Configure ADC for maximum speed
  adc->adc1->setAveraging(0);
  adc->adc1->setResolution(12);
  adc->adc1->setConversionSpeed(ADC_CONVERSION_SPEED::VERY_HIGH_SPEED);
  adc->adc1->setSamplingSpeed(ADC_SAMPLING_SPEED::VERY_HIGH_SPEED);
  
  // Configure DMA for faster transfers
  dma1.source(ADC1_R0);
  dma1.destinationBuffer(drillBuffer, sizeof(drillBuffer));
  dma1.triggerAtHardwareEvent(DMAMUX_SOURCE_ADC1);
  dma1.attachInterrupt(dma1_isr);
  dma1.interruptAtCompletion();
  dma1.enable();
  
  // Start continuous ADC conversions
  adc->adc1->startContinuous(DRILL_CURRENT_PIN);
  
  while (!Serial);
}

void loop() {
  if (newData) {
    uint16_t rawDrill = drillBuffer[bufferIndex];
    uint16_t rawPower = analogRead(POWER_CURRENT_PIN);
    uint16_t rawLinear = analogRead(LINEAR_CURRENT_PIN);
    
    float currDrill = rawDrill * DRILL_TO_AMP;
    float currPower = rawPower * POWER_TO_AMP;
    float currLinear = rawLinear * LINEAR_TO_AMP;
    
    Serial.write((uint8_t*)&currDrill, sizeof(float));
    Serial.write((uint8_t*)&currPower, sizeof(float));
    Serial.write((uint8_t*)&currLinear, sizeof(float));
    Serial.write('\n');
    
    bufferIndex++;
    if (bufferIndex >= BUFFER_SIZE) {
      bufferIndex = 0;
    }
    newData = false;
  }
}