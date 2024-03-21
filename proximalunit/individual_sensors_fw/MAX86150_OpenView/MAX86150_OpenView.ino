/*
  ProtoCentral MAX86150 Breakout Board

  https://github.com/protocentral/protocentral_max86150

  Plots ppg and ECG signals through protocentral openview GUI
  GUI URL: https://github.com/Protocentral/protocentral_openview.git
*/
#include <Arduino.h>
#include <FIR.h>
#include <Wire.h>
#include "max86150.h"

#define CES_CMDIF_PKT_START_1   0x0A
#define CES_CMDIF_PKT_START_2   0xFA
#define CES_CMDIF_TYPE_DATA     0x02
#define CES_CMDIF_PKT_STOP      0x0B
#define DATA_LEN                6
#define ZERO                    0


MAX86150 max86150Sensor;


FIR<long, 13> fir;

/*

FIR filter designed with
 http://t-filter.appspot.com

sampling frequency: 200 Hz

fixed point precision: 16 bits

* 0 Hz - 1 Hz
  gain = 0
  desired attenuation = -40 dB
  actual attenuation = n/a

* 2 Hz - 25 Hz
  gain = 1
  desired ripple = 10 dB
  actual ripple = n/a

* 26 Hz - 100 Hz
  gain = 0
  desired attenuation = -40 dB
  actual attenuation = n/a

*/
long coef[13] = {
	-364,
	-103,
	-42,
	60,
	173,
	262,
	295,
	262,
	173,
	60,
	-42,
	-103,
	-364
 };
// Sampling frequency
const double f_s = 200; // Hz
// Cut-off frequency (-3 dB)
const double f_c = 50; // Hz
// Normalized cut-off frequency
const double f_n = 2 * f_c / f_s;

volatile char DataPacket[16];
const char DataPacketFooter[2] = {ZERO, CES_CMDIF_PKT_STOP};
const char DataPacketHeader[5] = {CES_CMDIF_PKT_START_1, CES_CMDIF_PKT_START_2, DATA_LEN, ZERO, CES_CMDIF_TYPE_DATA};


uint16_t irunsigned16;
uint16_t redunsigned16;
int16_t  ecgsigned16;


void sendDataThroughUart(){

  DataPacket[0] = ecgsigned16;
  DataPacket[1] = ecgsigned16 >> 8;

  DataPacket[2] = irunsigned16;
  DataPacket[3] = irunsigned16 >> 8;

  DataPacket[4] = redunsigned16;
  DataPacket[5] = redunsigned16 >> 8;

  //send packet header
  for(int i=0; i<5; i++){

    Serial.write(DataPacketHeader[i]);
  }

  //send sensor data
  for(int i=0; i<DATA_LEN; i++){

    Serial.write(DataPacket[i]);
  }

  //send packet footer
  for(int i=0; i<2; i++){

    Serial.write(DataPacketFooter[i]);
  }
}

void setup()
{
    Serial.begin(57600);
    Serial.println("MAX86150 PPG Streaming Example");
    fir.setFilterCoeffs(coef);

    // Initialize sensor
    if (max86150Sensor.begin(Wire, I2C_SPEED_FAST) == false)
    {
        Serial.println("MAX86150 was not found. Please check wiring/power. ");
        while (1);
    }

  	Serial.println(max86150Sensor.readPartID());

    max86150Sensor.setup(); //Configure sensor. Use 6.4mA for LED drive
}

void loop()
{
    if(max86150Sensor.check()>0)
    {
				irunsigned16  = (uint16_t) (max86150Sensor.getFIFOIR()>>2);
				redunsigned16 = (uint16_t) (max86150Sensor.getFIFORed()>>2);
        ecgsigned16   = (int16_t)  fir.processReading((max86150Sensor.getFIFOECG()>>2));

        sendDataThroughUart();
    }
}
