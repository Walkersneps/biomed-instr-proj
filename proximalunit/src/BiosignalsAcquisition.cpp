#include <Arduino.h>
#include <Pins.h>

int16_t acquireSampleTemperature() {
    return analogRead(PIN_TEMPERATURE);
}

