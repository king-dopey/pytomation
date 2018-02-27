#!/usr/bin/python3
"""
File:
        rpi_gpio_remote.py

Description:

This is a server process for remote Raspberry Pis to use connect to.
It should work with all models of Raspberry Pi that have a network interface.

Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2018
License:
    This free software is licensed under the terms of the GNU public license, Version 3

Usage:
    Please see the documentation for the Pytomation RpiGpio interface for setting GPIO pins.

Notes:
    For documentation on the Raspberry Pi, see the Raspberry Pi official site:
    https://www.raspberrypi.org


Versions and changes:
    Initial version created on Feb 13, 2018
openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key -nodes -out selfsigned.cert -sha256 -days 1000
This is like telnet localhost:12345 but using your cert and key
openssl s_client -connect localhost:12345
"""

import ssl
import asyncio
import asyncio.streams
from .common import *
from .ha_interface import HAInterface

class RpiGpioRemote(HAInterface):
    VERSION = '1.0'
    # On all recent Raspberry Pi's only these pins are allowed as GPIO
    LEGAL_BCM_PINS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                      15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27)
    LEGAL_BOARD_PINS = (3, 5, 7, 11, 13, 15, 19, 21, 23, 27, 29, 31, 33, 35,
                        37, 8, 10, 12, 16, 18, 22, 24, 26, 28, 32, 36, 38, 40)

    def __init__(self, *args, **kwargs):
        super(RpiGpioRemote, self).__init__(None, *args, **kwargs)

    # Instance should be rpi = RpiGpioRemote(pin_layout='BOARD|BCM', address=None, port=None, ssl=None, secret=None)
    def _init(self, *args, **kwargs):
        super(RpiGpioRemote, self)._init(*args, **kwargs)
        self._pin_layout = kwargs.get('pin_layout', 'BOARD')
        self._ip_address = kwargs.get('address', None)
        self._ip_port = kwargs.get('port', None)
        self._secret = kwargs.get('secret', None)
        self._configured_pins = []
        self._pin_data = {}
        self.server = None  # encapsulates the server sockets
        self.c_reader = None
        self.c_writer = None

        rpissl = kwargs.get('ssl', (None,None)) # tuple of (cert, key)
        self.version()
        if rpissl != (None,None):
            self.sc = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.sc.load_cert_chain(rpissl[0], rpissl[1])
        else:
            self.sc=None

    def _start(self, loop):
        # Starts the TCP server
        self.server = loop.run_until_complete(
            asyncio.streams.start_server(self._accept_client,
                                         self._ip_address, self._ip_port,
                                         loop=loop, ssl=self.sc))

    def _stop(self, loop):
        print("Stopping RpiGpioRemote server...")
        if self.server is not None:
            self.server.close()
            loop.run_until_complete(self.server.wait_closed())
            self.server = None

    def run(self):
        print("Starting RpiGpioRemote server at {} on port {}...".format(self._ip_address, self._ip_port))
        loop = asyncio.new_event_loop()
        self._start(loop)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print(" ")
        finally:
            self._stop(loop)
            loop.close()


    def _accept_client(self, client_reader, client_writer):
        # start a new Task to handle this specific client connection
        self.c_writer = client_writer
        task = asyncio.Task(self._handle_client(client_reader, client_writer))

        def client_done(task):
            print("RpiGpioRemote client {} closed connection...".format(self._ip_address))

        task.add_done_callback(client_done)

    @asyncio.coroutine
    def _handle_client(self, client_reader, client_writer):
        self._secret_ok = False
        arg = None

        while True:
            data = (yield from client_reader.readline()).decode("utf-8")
            if not data: # an empty string means the client disconnected
                break
            # strip the command of any leading or trailing spaces and split
            # at first ':'
            if ':' in data:
                cmd, arg = data.rstrip().split(':',1)
            else:
                cmd = data.rstrip()
            if self._secret_ok:
                if cmd == 'on':
                    self._logger.debug("Received ON from client {} for pin {}....".format(int(arg),self._ip_address))
                    self._onCommand(address=int(arg), command=Command.ON)
                elif cmd == 'off':
                    self._logger.debug("Received OFF from client {} for pin {}....".format(int(arg),self._ip_address))
                    self._onCommand(address=int(arg), command=Command.OFF)
                elif cmd == 'get_board':
                    self._logger.debug("Received GET BOARD from client...".format(self._ip_address))
                    self.get_board(client_writer)
                elif cmd == 'get_pins':
                    self._logger.debug("Received GET PINS from client {}...".format(self._ip_address))
                    self.get_pins(client_writer)

            elif cmd == 'check_secret':
                print("Received CHECK SECRET from client {}...".format(self._ip_address))
                if arg == self._secret:
                    print("Shared secret is accepted...")
                    client_writer.write("Shared secret accepted\n".encode("utf-8"))
                    self._secret_ok = True
                else:
                    print("Bad shared secret from client {}...".format(self._ip_address))
                    client_writer.write("Shared secret does not match...\n".encode("utf-8"))
                    yield from client_writer.drain()
                    break
            else:
                self._logger.debug("Bad command {!r}".format(data))

            # This enables us to have flow control in our connection.
            yield from client_writer.drain()


    def get_board(self, client_writer):
        client_writer.write((self._pin_layout + '\n').encode("utf-8"))

    def get_pins(self, client_writer):
        if self._configured_pins == []:
            client_writer.write("Error\n".encode("utf-8"))
            self._logger.debug("You have not configured pins in the instance file...")
            return
        for pin in self._configured_pins:
            client_writer.write((pin + '\n').encode("utf-8"))
        client_writer.write('end\n'.encode("utf-8"))

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
                s = "{}:{}:{}:{}".format(pin,type,pud,invert)
                self._configured_pins.append(s)
                self._logger.debug("Set pin [{}] to INPUT / {} with {} ms debounce...".format(pin,pud,debounce))
            elif type == 'OUT':
                if init == 'LOW' or init == 'HIGH':
                    s = "{}:{}:{}".format(pin, type, init)
                    self._configured_pins.append(s)
                else:
                    self._logger.debug("Initial value while setting pin [ " + str(pin) + " ] is illegal...")
                    return
                self._logger.debug("Set pin [{}] to OUTPUT, with initial value of {}...".format(pin,init))
            else:
                self._logger.debug("Illegal pin direction [" + type + "] must be \'IN\' or \'OUT\'...")


    def on(self, address):
        if self._secret_ok:
            self.c_writer.write(("{}:ON\n".format(address)).encode('utf-8'))
        else:
            self._logger.debug("Shared secret check failure, not sending command...")
    def off(self, address):
        if self._secret_ok:
            self.c_writer.write(("{}:OFF\n".format(address)).encode('utf-8'))
        else:
            self._logger.debug("Shared secret check failure, not sending command...")

    def version(self):
        self._logger.info("RpiGpioRemote Pytomation interface version {}".format(self.VERSION))



