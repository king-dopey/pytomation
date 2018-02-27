#!/usr/bin/python3
"""
File:
        rpi_remote_client.py

Description:

This is a client for remote Raspberry Pis to use connect to Pytomation running
the RpiGpioRemote interface.

It should work with all models of Raspberry Pi that have a network interface.

Author(s):
         George Farris <farrisg@gmsys.com>
         Copyright (c), 2018
License:
    This free software is licensed under the terms of the GNU public license, Version 3

Usage:
    Please see the documentation for the Pytomation RpiGpioRemote interface for setting GPIO pins.
    This client auto connects to your Pytomation instance and is auto configured.

    Settable parameters:

    host=<string>       Host name or IP address of your Pytomation server.
    port=<int>          IP port of your Pytomation server.
    secret=<string>     Shared secret contained both here and on your server.  This is a string that should
                        be between 8 and 32 characters in length and contains ascii printable characters.
    sslcert=<string>    Optional path to an openssl cert for encrypting the link.  You do not require
                        encryption. but you do require the shared secret.

    Openssl certifcate and key pairs can be created with the following command:
        openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key -nodes -out selfsigned.cert -sha256 -days 1000

    Your Pytomation server must have both, the client only requires the cert file.

    When generating a cert|key pair you should use the host name of your Pytomation server.  Here is
    an example:

    $ openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key -nodes -out selfsigned.cert -sha256 -days 1000
    Generating a 2048 bit RSA private key
    ......................................................+++
    ......+++
    writing new private key to 'selfsigned.key'
    -----
    You are about to be asked to enter information that will be incorporated
    into your certificate request.
    What you are about to enter is what is called a Distinguished Name or a DN.
    There are quite a few fields but you can leave some blank
    For some fields there will be a default value,
    If you enter '.', the field will be left blank.
    -----
    Country Name (2 letter code) [AU]:CA
    State or Province Name (full name) [Some-State]:British Columbia
    Locality Name (eg, city) []:Victoria
    Organization Name (eg, company) [Internet Widgits Pty Ltd]:Personal
    Organizational Unit Name (eg, section) []:
    Common Name (e.g. server FQDN or YOUR name) []:pytomation    <---your server host name or ip
    Email Address []:

    Store your cert file in the same location as this file.

Notes:
    For documentation on the Raspberry Pi, see the Raspberry Pi official site:
    https://www.raspberrypi.org


Versions and changes:
    Initial version created on Feb 13, 2018

This is like telnet localhost:12345 but using your cert and key
openssl s_client -connect localhost:12345
"""

import os
import sys
import ssl
import asyncio
import RPi.GPIO as GPIO

# --------------------- User configurable settings ---------------------------------
#host = '127.0.0.1'
host = '199.60.63.2'
port = 8088
secret = 'my shared secret'
#sslcert = './mycert.cert'
sslcert = None

# ===================== End of user configurable settings ==========================
VERSION = '1.0'

@asyncio.coroutine
def conn(loop):
    if sslcert != None and not os.path.isfile(sslcert):
        print("You certificate file {} seems to be missing...".format(sslcert))
        sys.exit()

    if sslcert != None:
        sc = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
            cafile=sslcert)
    else:
        sc=None

    print("Opening connection to {} on port {}...".format(host, port))
    try:
        reader, writer = yield from asyncio.open_connection(
                host, port, ssl=sc, loop=loop)
        print("Connected...")
    except:
        print("Connection Failed, check your host name or IP address and port...")
        sys.exit()


    # Send the server our shared secret and wait for a response
    print("Sending shared secret...")
    s = 'check_secret:'+ secret+'\n'
    writer.write(s.encode())
    yield from writer.drain()
    rsp = yield from reader.readline()
    data = rsp.decode().rstrip('\n')
    if data != 'Shared secret accepted':
        print("Shared secret is NOT accepted, please check they are the identical on each end...")
        print("Closing connection and exiting...")
        sys.exit()
    else:
        print("Server accepted shared secret from remote...")

    # Get the GPIO pin layout which should be BCM or BOARD and set it on the Pi
    # --------------------------------------------------------------------------
    print("Sending get_board command...")
    writer.write('get_board\n'.encode())
    yield from writer.drain()
    rsp = yield from reader.readline()
    data = rsp.decode().rstrip('\n')

    if data == 'BCM':
        print("Received pin layout type BCM from server...")
        GPIO.setmode(GPIO.BCM)
    elif data == 'BOARD':
        print("Received pin layout type BOARD from server...")
        GPIO.setmode(GPIO.BOARD)
    else:
        print("Received incorrect GPIO layout type, must be BCM or BOARD...")
        print("Closing connection and exiting...")
        sys.exit()

    # Get the GPIO pin settings
    # --------------------------------------------------------------------------
    pin_data = {}
    configured_input_pins = []

    print("Sending get_pins command...")
    writer.write('get_pins\n'.encode())
    yield from writer.drain()

    while True:
        rsp = yield from reader.readline()
        if not rsp:
            break
        data = rsp.decode().rstrip('\n')
        if 'Error' in data:
            print("You have not configured pins in the instance file...")
            break
        elif data == 'end': # all the pins have been sent
            print("All pins configured...")
            break
        pin, type, *args = data.split(':')
        # input pin will be  -> pin:type:pud:invert
        # output pin will be -> pin:type:init

        if type == 'IN':
            if args[0] == 'PULL_UP':
                pud = GPIO.PUD_UP
            else:
                pud = GPIO.PUD_DOWN
            GPIO.setup(int(pin), GPIO.IN, pull_up_down=pud)
            configured_input_pins.append(int(pin))
            if len(args) == 2:
                if args[1] == 'True':
                    pin_data.update({int(pin): {'state': 'unknown', 'invert': True}})
                else:
                    pin_data.update({int(pin): {'state': 'unknown', 'invert': False}})
            print("Setting pin {} to type {} with bias {} and invert state of {}...".format(pin,type, args[0],args[1]))
        else:
            print("Setting pin {} to type {} with initial state of {}...".format(pin, type, args[0]))
            if args[0] == 'LOW':
                GPIO.setup(int(pin), GPIO.OUT, initial=0)
            else:
                GPIO.setup(int(pin), GPIO.OUT, initial=1)

    return reader,writer,configured_input_pins,pin_data


@asyncio.coroutine
def rcvr(r):
    print("Dropping into receive loop...")
    while True:
        rsp = yield from r.readline()
        pin, *args = rsp.decode().rstrip().split(':', 1)
        if args[0] == 'ON':
            GPIO.output(int(pin), GPIO.HIGH)
            print("Pin {} remotely set to {}".format(pin, args[0]))
        elif args[0] == 'OFF':
            GPIO.output(int(pin), GPIO.LOW)
            print("Pin {} remotely set to {}".format(pin, args[0]))
        elif args[0] == 'RESET':
            pass
        yield from asyncio.sleep(.1)


@asyncio.coroutine
def xmtr(w,configured_input_pins,pin_data):
    ON = 1
    OFF = 0

    print("Dropping into transmitter loop...")
    while True:
        yield from asyncio.sleep(0.05)  # need this to yield control back to the loop
        for pin in configured_input_pins:
            pin_state = GPIO.input(pin)
            if pin_state != pin_data[pin]['state']:
                print("Pin {} changed state to {}".format(pin,pin_state))
                pin_data[pin]['state'] = pin_state
                if pin_state:
                    state = ON
                else:
                    state = OFF
                # flip the value if inverted
                if pin_data[pin]['invert']:
                    state ^= ON
                if state == ON:
                    w.write(("on:{}\n".format(pin)).encode())
                else:
                    w.write(("off:{}\n".format(pin)).encode())
                yield from w.drain()


if __name__ == '__main__':
    print("Raspberry Pi Pytomation remote client, version {}".format(VERSION))
    print("For use with RpiGPIORemote interface...\n")
    try:
        loop = asyncio.get_event_loop()
        reader,writer,pins,pin_data = loop.run_until_complete(conn(loop))
        tasks = [loop.create_task(rcvr(reader)), loop.create_task(xmtr(writer,pins,pin_data))]
        wait_tasks = asyncio.wait(tasks)
        loop.run_until_complete(wait_tasks)
    except KeyboardInterrupt:
        print("Quiting...")
        GPIO.cleanup()
    finally:
        loop.close()
    # Just in case
    GPIO.cleanup()

