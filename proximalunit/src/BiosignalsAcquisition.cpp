#include <Arduino.h>
#include <max86150.h>
#include <Pins.h>


uint16_t acquireSampleECG() {
    Serial.print("Sampling happens here...");
}

uint16_t acquireSampleTemperature() {
    return analogRead(PIN_TEMPERATURE);
}

