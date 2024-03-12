# Portable Physiological Signals Monitor
## Walter Carli and Dario Lucchini
### Biomedical Instrumentation Project [717.318]
#### TU Graz
##### Academic Year 2023-2024 Winter Semester

#

Implementation of a portable and non-invasive system for acquiring some physiological signals and displaying their values in real-time.

Developed for the course _Biomedical Instrumentation Project_ offered at TU Graz.

#
#### Folder Structure
 - Folder `proximalunit` contains the firmware needed for the operation of the MCU which directly interfaces with the sensors and the sensor breakout boards, while sending the read data to the _remote unit_.  
 In our implementation, an ESP32 development board was used for this purpose.

 - Folder `remoteunit` contains the source code of the software needed to collect data from the _proximal unit_ and display it to the user.
