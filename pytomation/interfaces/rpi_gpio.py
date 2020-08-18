"""
File:
        rpi_gpio.py

Description:

This is a driver for the Raspberry Pi GPIO pins.  It should work with all models of Raspberry Pi.

The the GPIO pins on the RPi board are set according to the following:

Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2018

         Functions common to Pytomation written by:
         Jason Sharpee <jason@sharpee.com>

License:
    This free software is licensed under the terms of the GNU public license, Version 3

Usage:
    There are two ways of numbering the IO pins on a Raspberry Pi. The first is using the
    BOARD numbering system which equates to the physical pin numbers on the P1 header of
    the Raspberry Pi.

    The second is using the BCM numbering systems which equates to the Broadcom chip GPIO
    numbering scheme.

    The advantage of using the BOARD numbering system is that your hardware will always work,
    regardless of the board revision of the RPi. You will not need to rewire your connector
    or change your code. I have, however, noticed that many projects seem to use the BCM scheme.

    You may choose either one.

    GPIO pins on the 40 pin header are as follows:
               3V3  (1) (2)  5V
             GPIO2  (3) (4)  5V
             GPIO3  (5) (6)  GND
             GPIO4  (7) (8)  GPIO14
               GND  (9) (10) GPIO15
            GPIO17 (11) (12) GPIO18
            GPIO27 (13) (14) GND
            GPIO22 (15) (16) GPIO23
               3V3 (17) (18) GPIO24
            GPIO10 (19) (20) GND
             GPIO9 (21) (22) GPIO25
            GPIO11 (23) (24) GPIO8
               GND (25) (26) GPIO7
             GPIO0 (27) (28) GPIO1
             GPIO5 (29) (30) GND
             GPIO6 (31) (32) GPIO12
            GPIO13 (33) (34) GND
            GPIO19 (35) (36) GPIO16
            GPIO26 (37) (38) GPIO20
               GND (39) (40) GPIO21


    In your instance file setup interface and pins as follows:
    # Pytomation running on this raspberry pi with pin layout of type BCM
      rpi = RpiGpio(pin_layout='BCM', address=None, port=None, poll=None)
    # pin_layout can be BCM or BOARD

    # Address , port and poll time are not used yet, this interface only
    # supports Pytomation running locally on the RPi.

    # Set the I/O points as INPUTS or OUTPUTS with optional debounce in
    # milliseconds, invert for INPUTS and initial state for OUTPUTS
    #
    # These examples use type BOARD pins

    # Set pin 3, GPIO-2 as INPUT with pullup resister, inverted state and
    # 100ms debounce.
      rpi.setPin(3, 'IN', pud='PULL_UP', invert=True ,debounce=100)

    # Set pin 5, GPIO-3 as INPUT with pulldown resister and 200ms debounce
      rpi.setPin(5, 'IN', pud='PULL_DOWN', debounce=200)

    # Set pin 7, GPIO-4 as OUTPUT, with initial value set to LOW state
      rpi.setPin(7, 'OUT') or rpi.setPin(7, 'OUT', init='LOW')

    # Set pin 7, GPIO-4 as OUTPUT, with initial value set to HIGH state
      rpi.setPin(7, 'OUT', init='HIGH')

    Please note that INVERT on an input is particularly useful when an input is pulled
    high and the pin must be grounded to operate.  INVERT does not change the value of
    the pin just the ON state within Pytomation

    Using the pins in the instance file:

    This is used just like any other Pytomation interface.  Example:

    #Inputs
    m_room_motion = Motion(address=17,
                       devices=rpi,
                       name="Room motion detectormytest")
    # Outputs
    l_room_lamp = Light(address=26,
                    devices=(rpi),
                    name='Room Lamp')


Notes:
    For documentation see the Raspberry Pi official site:
    https://www.raspberrypi.org


Versions and changes:
    Initial version created on Feb 09 , 2018

"""
import time
import RPi.GPIO as GPIO
from .common import *
from .ha_interface import HAInterface


class RpiGpio(HAInterface):
    VERSION = '1.0'
    # On all recent Raspberry Pi's only these pins are allowed as GPIO
    LEGAL_BCM_PINS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                      15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27)
    LEGAL_BOARD_PINS = (3, 5, 7, 11, 13, 15, 19, 21, 23, 27, 29, 31, 33, 35,
                        37, 8, 10, 12, 16, 18, 22, 24, 26, 28, 32, 36, 38, 40)

    def __init__(self, *args, **kwargs):
        super(RpiGpio, self).__init__(None, *args, **kwargs)

    # Instance should be rpi = RpiGpio(pin_layout='BOARD|BCM', poll=None)
    def _init(self, *args, **kwargs):
        super(RpiGpio, self)._init(*args, **kwargs)
        self._pin_layout = kwargs.get('pin_layout', 'BOARD')
        self._ip_address = kwargs.get('address', None)
        self._ip_port = kwargs.get('port', None)
        self._poll_secs = kwargs.get('poll', 5)
        self._configured_pins = []
        self._pin_data = {}

        self.version()

        # check the pin layout type and set the mode
        if self._pin_layout == 'BOARD':
            GPIO.setmode(GPIO.BOARD)
            self._logger.debug("Setting pin layout to type \'BOARD\'...")
        elif self._pin_layout == 'BCM':
            self._logger.debug("Setting pin layout to type \'BCM\'...")
            GPIO.setmode(GPIO.BCM)
        else:
            self._logger.debug(
                "Illegal pin layout [" + self._pin_layout + "] must be of type \'BOARD\' or \'BCM\' ...")
            print("[RpiGpio] Illegal pin layout [" + self._pin_layout + "] must be of type \'BOARD\' or \'BCM\' ...")
            sys.exit()


    def _readInterface(self, lastPacketHash):
        # check to see if there is anything we need to read
        for pin in self._configured_pins:
            pin_state = GPIO.input(pin)
            if pin_state != self._pin_data[pin]['state']:
                if pin_state:
                    contact = Command.ON
                else:
                    contact = Command.OFF
                # flip the value if inverted
                if self._pin_data[pin]['invert']:
                    contact = contact is Command.ON and Command.OFF or Command.ON
                self._pin_data[pin]['state'] = pin_state
                self._logger.debug("Command is " + contact + '\n')
                self._onCommand(address=pin, command=contact)
        time.sleep(0.1)

    def _checkLegalPins(self, pin):
        if self._pin_layout == 'BCM':
            if pin not in self.LEGAL_BCM_PINS:
                self._logger.debug("Illegal pin number for pin layout of type " + self._pin_layout + "...\n")
                return False
        elif pin not in self.LEGAL_BOARD_PINS:
            self._logger.debug("Illegal pin number for pin layout of type " + self._pin_layout + "...\n")
            return False
        return True

    # Initialize the Raspberry Pi GPIO pins as inputs or outputs.
    def setPin(self, pin, type, pud=None, invert=False, debounce=25, init='LOW'):
        if self._checkLegalPins(pin):   # pin is valid
            if type == 'IN':
                if pud == 'PULL_UP':
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    self._logger.debug("Set pin [" + str(pin) + "] to INPUT / PULL_UP with " + str(debounce) + "ms debounce...")
                elif pud == 'PULL_DOWN':
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    self._logger.debug("Set pin [" + str(pin) + "] to INPUT / PULL_DOWN with " + str(debounce) + "ms debounce...")
                self._pin_data.update({pin: {'state': 'unknown', 'invert': invert}})
                self._configured_pins.append(pin)
            elif type == 'OUT':
                if init == 'LOW':
                    GPIO.setup(pin, GPIO.OUT, initial=0)
                elif init == 'HIGH':
                    GPIO.setup(pin, GPIO.OUT, initial=1)
                else:
                    self._logger.debug("Initial value while setting pin [ " + str(pin) + " ] is illegal...")
                    return
                self._logger.debug("Set pin [" + str(pin) + "] to OUTPUT, with initial value of " + init + "...")
            else:
                self._logger.debug("Illegal pin direction [" + type + "] must be \'IN\' or \'OUT\'...")

    def on(self, address):
        GPIO.output(address, GPIO.HIGH)

    def off(self, address):
        GPIO.output(address, GPIO.LOW)

    def version(self):
        self._logger.info("RpiGpio Pytomation driver version " + self.VERSION + '\n')
