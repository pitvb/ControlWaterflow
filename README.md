# ControlWaterflow

Challenge :
- Ensure that the water softening device will be reset if waterflow during backwash is lasting for more then x (set to 180) seconds.
- Reset is done by power of ... wait 10 seconds ... power on
- The Gravity water flow sensor has a limit of 30 liter per minute while the backwash for some time does produce 150 liters per minute

Used devices :
- Raspberry PI 3
- Single channel relais module
- Gravity Water Flow Sensor (1/2")
- Printed device to ensure that the water flow through the sensor does not exceed the limit

Further challenges :
The distance between the flow sensor and the raspberry was quite long and there are a couple of devices in between which did cause electrical spikes to the cable.
For the GPIO port of the raspberry allows only 3.3 volt on the line and the raspberry did show some "waterflows" where there where none. As I had only limited time
to create a stable system, I decided to connect the waterflow senor to an Arduino, close to the sensor and with a relay, connected to the Arduino make sure that the line is stable on the rquired level.
Electrical scema will follow.
I will further try to find out if my assumption (spikes on the line) is correct. I have time now as the system is running very stable since weeks now.

