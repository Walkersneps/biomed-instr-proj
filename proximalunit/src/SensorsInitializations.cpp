#include <Arduino.h>
#include <max86150.h>
#include <Wire.h>

extern bool max86150Initialized = false;

void initializeMAX86150(MAX86150 sensor) {
    Serial.println(F("[MAX86150] Setup of MAX86150 Board (for ECG and PPG)"));
    
    while (!sensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println(F("[MAX86150] [ERROR] Board not found. Retrying in 2 seconds..."));
        delay(2000);
    }
    Serial.print(F("[MAX86150] Board found! PartID is: "));
    Serial.println(sensor.readPartID());

    sensor.setup();
    max86150Initialized = true;
}