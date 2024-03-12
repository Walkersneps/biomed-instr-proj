#include <cstring>
#include <string>
#include <Arduino.h>
#include <max86150.h>
#include <secrets.h>
#include <BluetoothSerial.h>
#include <unordered_map>
#include <SensorsInitializations.h>

// ## o-o-o-o SETTINGS o-o-o-o ##
// ##############################
// ###  Biosignals Settings  ###
#define NSIGNALS 5 // How many signals we're acquiring

// ###  Serial Port Settings  ###
#define SERIAL_BAUDRATE 115200

// ###  Bluetooth Settings  ###
#define BT_DEVNAME "ESP32_BT"
// ###############################
// o-o-o-o END of SETTINGS o-o-o-o

// Bluetooth Objects
BluetoothSerial SerialBT;

// FreeRTOS Tasks
void vTask_SampleMAX86150(void *pvParameters) {
  // Recover settings
  //JsonObject config = *static_cast<JsonObject *>(pvParameters);
  const double fsample = 220;//config["fsample"].as<float>();
  const int overlay = 20;//config["overlay"].as<int>();
  const int npacket = 200;//config["npacket"].as<int>();

  // Initialize sensor
  MAX86150* max86150 = new MAX86150();
  initializeMAX86150(max86150);

  // Check that we have everything we need
  const bool dataOk = (fsample && overlay && npacket);
  if (!dataOk) { Serial.print(F("[ERROR] Uncastable settings for ECG")); }

  while (dataOk) {
    if (max86150->check() > 0) { // check() polls the sensor, and saves all the available samples in the local FIFO.
      //while (max86150->available()) { // available() checks the local FIFO, and returns (head-tail).
      /* Note on MAX86150 data!
        * The data that then sensor outputs is  3-byte-long (24bit),
        * although the actual useful datum is always either 18 (for ECG) or 19 (for PPG) bits long.
        * 
        * The library we're using returns those in `uint32_t` datatype to fit the whole 24bits,
        * while masking the unused MSBs of each datum to 0.
        * 
        * Accepting to lose 2 LSBs of resolution, we can fit the data in 16bits, just by shifting
        * to the right 2 positions.
        */
        //Serial.printf("[ECG] saving data @idx %d...", sampleIndex);
        SerialBT.println(max86150->getFIFOECG() >> 2);
    }
  }
}




void setup() {
  Serial.begin(SERIAL_BAUDRATE);
  Serial.println(F("[SETUP] Hello! Setup in progress..."));

  Serial.println(F("[SETUP] Setupping Bluetooth"));
  SerialBT.begin(BT_DEVNAME);

  Serial.println(F("[SETUP] Done :-)"));

  // Create Sampling tasks
  xTaskCreatePinnedToCore(vTask_SampleMAX86150, "task_ECG", 2048, NULL, 10, NULL, APP_CPU_NUM);
} // end setup()




void loop() {

} // end loop()