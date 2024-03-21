#include <Arduino.h>
#include <Wire.h>
#include <protocentral_TLA20xx.h>

#define TLA20XX_I2C_ADDR 0x49
#define NSAMPLES 10

float avg;
float total = 0;
float samples[NSAMPLES] = {0};
int idx = 0;

TLA20XX tla2024(TLA20XX_I2C_ADDR);

void setup() 
{
    Serial.begin(57600);
    Serial.println("Starting ADC...");

    //Wire.setSDA(4);
    //Wire.setSCL(5);

    Wire.begin();

    tla2024.begin();
    
    tla2024.setMode(TLA20XX::OP_CONTINUOUS);


    tla2024.setDR(TLA20XX::DR_128SPS);
    tla2024.setFSR(TLA20XX::FSR_2_048V);

    // Set default channel as AIN0 <-> GND
    tla2024.setMux(TLA20XX::MUX_AIN0_GND);    
}

float val;

void loop() 
{
    float val = tla2024.read_adc(); // +/- 2.048 V FSR, 1 LSB = 1 mV

    // Moving Average Filter
    total = total - samples[idx];
    samples[idx] = val;
    total = total + samples[idx];
    avg = total / NSAMPLES;

    idx += 1;
    if (idx >= NSAMPLES) idx = 0;

    Serial.println(avg);
    
    delay(100);
}
