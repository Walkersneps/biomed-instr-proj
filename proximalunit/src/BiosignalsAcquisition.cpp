#include <Arduino.h>
#include <max86150.h>
#include <Pins.h>
#include <sharedObjects.h>


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

int16_t acquireSampleECG() {
    if (max86150.check() > 0)
        return (max86150.getECG() >> 2);
        
    return 0;
}

int16_t acquireSampleTemperature() {
    return analogRead(PIN_TEMPERATURE);
}

