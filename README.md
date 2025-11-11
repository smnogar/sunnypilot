![](https://user-images.githubusercontent.com/47793918/233812617-beab2e71-57b9-479e-8bff-c3931347ca40.png)

## Sunnypilot - BMW

This is a fork of sunnypilot for BMWs running SP2018. This has been tested on a BMW i4 (G26). 

It uses a Raspberry Pi Pico 2 to intercept flexray data between the SAS and BDC. When receiving steering commands from Openpilot, it injects those commands and sends them to the vehicle.

## Credits

This work heavily leverages the work of [dynm](https://github.com/dynm) and [CzokNorris](https://github.com/CzokNorris). They deserve most of the credit here.

## Warnings

This is a very experimental branch of Sunnypilot, and has not been subjected to the same safety standards as cars supported by Comma.

Ongoing issues:

* Tuning is needed
* I experience steering drop outs every 5-10 minutes.

## Requirements

* BMW running SP2018 (G20, G26, G30, etc). These are cars that advertise having "Driver Assistance Professional" with traffic jam assistant with hands free driving up to 40 MPH. 
* This uses CzokNorris' v1 flexray adapter board. References:
  * [OSHWLab](https://oshwlab.com/czoknorris/v1board)
  * [Schematic](https://github.com/CzokNorris/OpenFSD/tree/main/Hardware/FlexRayRPIPanda/Rev1)
* A Comma 3 (not 3X or 4). I will make a new branch once I get my Comma 4. 

## Making a Harness

You have to make your own harness. The harness sits between the SAS (steering ECU) and Body domain controller (BDC). It is  a 26 pin connector that I purchased from [aliexpress](https://www.aliexpress.us/item/3256805095325163.html?spm=a2g0o.order_list.order_list_main.5.58f31802709VtE&gatewayAdapt=glo2usa). Note that I did have to sand down one of the plastic nubs on the female connector to fit in the SAS. You can purchase these crimped or uncrimped and make your own cable. I purchased them prewired. 

![harness](docs/assets/harness-pic.jpeg)

WARNING: This harness picture does not include the CAN going into CAN 0. Make sure yours has this.

Czok's v1 board uses JST HY style connectors. Here are some tips for making them correctly:

- Use 22 gauge silicone wires. This allows for more flexibility and durability. I used - [BNTECHGO 22 Gauge Silicone Wire Kit 10 Color Each 5 ft Flexible 22 AWG Stranded Tinned Copper Wire](https://www.amazon.com/dp/B09X45S4L1?ref=ppx_yo2ov_dt_b_fed_asin_title)
- Make sure to use JST HY 2 mm pitch 4 pin connectors. I bought [CQRobot JST HY 2.0 mm Pitch 4-Pin Electronic Connector IC Male Plugs, Female Sockets Housing and T-Shaped Crimp Terminal Kit. 50 Sets/300 Pieces Wire-to-Board Adapter Cable Assembly.](https://www.amazon.com/dp/B0FCXL4S8P?ref=ppx_yo2ov_dt_b_fed_asin_title)
- Make sure when you crimp that the end of the connector is gripping the silicone shielding
- It helps to have some 20-30 cm of slack between the 26 pin connector and the PCB. THis makes it easier to maneuver the PCB around inside the car during installation.

### Wiring

Its necessary to tap the KCAN line and intercept the flexray data. Here is the wiring:

| Pin           | Label                 | CZ pico board | SAS <-> BDC Passthrough? |
| ------------- | --------------------- | ------------- | ------------------------ |
| 2             | Ground                | U6 G          | Yes                      |
| 3             | 12 V                  | U6 +          | Yes                      |
| 7             | KCAN Low              | Can 0 L       | Yes                      |
| 20            | KCAN High             | CAN 0 H       | Yes                      |
| SAS 8         | SAS Flexray M (low)   | Flexray 2 M   | No                       |
| SAS 9         | SAS Flexray P (high)  | Flexray 2 P   | No                       |
| Vehicle/BDC 8 | Vehicle/BDC Flexray M | Flexray 1 M   | No                       |
| Vehicle/BDC 9 | Vehicle/BDC Flexray P | Flexray 1 P   | No                       |

Any pin not labeled here MUST be connected. There is other data like ethernet that must go between SAS and BDC.

The micro-USB port from the Raspberry Pi pico must go to the Comma secondary USB-C port. The OBD-C connector must go to the Comma main USB-C port. Note that this cable must be a 10 gbps style cable with all internal connectors present.

![harness-diagram](docs/assets/harness-diagram.jpg)

## Flash Software on the Pico

1. Install the [PICO SDK](https://github.com/raspberrypi/pico-sdk) on your system

2. Make sure the pico is plugged in and run:

   ```
   cd pico-flexray
   mkdir build
   cd build
   export PICO_SDK_PATH=PATH_TO_YOUR_SDK
   cmake -G "Ninja" ..
   ninja
   picotool load -f pico_flexray.uf2
   ```

[See more details at dynm's pico-flexray repo](https://github.com/dynm/pico-flexray).

### Reset to bootloader mode

If you have installed the raspberry pi pico in the car and need to get it back to bootloader mode, run:

```
cd pico-flexray
python3 reset_to_bootloader.py
```

## Installation in Car

This probably only applies to BMW 3 and 4 series (i.e. G20, G26, etc).

- My car is an EV, so it’s **very important** to disconnect the high voltage battery before the 12 V battery. There are instructions how to do this online
- I have a technician guide from BMW on how to replace the SAS if anyone wants it.
- The SAS is in the drivers footwell
- I didn’t fully disconnect the trim piece that is above the pedals, just undid the 2 screws and pulled it out.
  - When this piece is off, the car won’t stay in the “ON” mode if your foot is off the brake
- SAS is held in by 2 bolts. The top one is pretty hard to reach. I managed to get the connector out by disconnecting the bottom bolt only. 
- I placed CZ’s board in an anti-static bag and then left it in the cavity behind the SAS module. Eventually I should secure it to something
- After reconnecting the 12 V then the HV battery, it’s normal to get parking sensor errors but you should not get driver assist errors. The parking sensor errors should go away after a few min of driving.

## Running Sunnypilot

1. Once this is all complete, you will need to flash your Comma with this branch of software. I had issues getting my Comma to clone this repo directly, so you may need to flash it with sunnypilot/master-tici and then manually push this branch via SSH.
2. You will have to manually select your vehicle. Currently supported vehicles are G26 and G30.
3. Run your vehicle with the stock LKAS system disabled, i.e. ACC mode only.

## Other Notes

1. This branch contains a modified version of Cabana that can process flexray data without crashing.
2. With this installation, the comma will only be powered on when the car is powered on.

## Resources

* Dynm: [pico-flexray](https://github.com/dynm/pico-flexray), [sunnypilot fork](https://github.com/dynm/sunnypilot)
* [Guide from Gerico](https://github.com/dynm/pico-flexray/discussions/3)
* Discord:
  * [Openpilot car port](https://discord.com/channels/469524606043160576/1399674371177578516)
  * [Sunnypilot BMW](https://discord.com/channels/880416502577266699/1420418454502113360)
