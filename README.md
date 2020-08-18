# Pytomation

---

Pytomation is an extensible device communication and automation system written in Python. It's uses 
include home automation and lighting control but is certainly not limited to 
that.  It is supported on any platform that support Python ( Windows, Mac OS-X, Linux, etc )

#### Supported
Pytomation currently has support for the following hardware interfaces with 
more planned in the future.

   - [Insteon PLM](http://www.insteon.com/) / X10 (2412N, 2412S, 2413U)
   - [Insteon Hub](http://www.insteon.com/) (2245-222, possibly others)
   - [UPB](http://www.pulseworx.com/products/products_.htm) Universal Powerline Bus (Serial PIM)
   - [Belkin WeMo](http://www.belkin.com/us/Products/home-automation/c/wemo-home-automation)  WeMo Wifi Switches 
   - [JDS Stargate](http://www.jdstechnologies.com/stargate.html) (RS232 / RS485)
   - [Radio Thermostat](http://www.radiothermostat.com/ ) WiFi Enabled Thermostat (CT30)
   - [Nest Labs](https://nest.com/) Nest thermostat
   - [Venstar ColorTouch](http://www.venstar.com/Thermostats/ColorTouch/) Thermostat (5/6800)
   - [Weeder](http://www.weedtech.com/) Digital I/O board (Wtdio/RS232)
   - [Logitech Harmony](http://www.myharmony.com) Universal WiFi Remote (Harmony Ultimate)
   - [WGL Designs](http://wgldesigns.com/w800.html) W800RF32 X10 RF receiver (W800/RS232)
   - [Arduino](http://www.arduino.cc) Uno board (USB)
   - [X10](http://x10pro-usa.com/x10-home/controllers/wired-controllers/cm11a.html) CM11a (RS232)
   - Mochad X10 CM15 (USB) and CM19 (USB)
   - [Misterhouse](http://misterhouse.sourceforge.net/) Voice Commands MHSend (TCP)
   - [Spark I/O](http://www.spark.io) WiFi devices
   - Z-Wave (Aeon Labs via python-Openzwave) DSA02203-ZWUS 
   - [Phillips HUE](http://www.meethue.com) Phillips HUE, Zigbee lighting

### FEATURES
   - Written in Python 3
   - REST API
   - Mobile Web and Android clients w/ continuous device state updates (web-sockets)
   - Voice Commands from Android (“Home Control” app)
   - Restrictive User security (beyond the current admin user)
   - Local Telnet and Web access
   - Unique language to describe devices and actions
   - Smart objects: Doors, Lights, Motion, Photocell etc.
   - Optional “Mainloop” programming, for more complicated control
   - Optional “Event driven” programming, for complex actions when a device state changes
   - Time of day on and off control
   - Delays for time off
   - Idle command, device will return to "idle" state
   - Map one command to another with optional source and time
   - Good hardware support with more coming
   - Very easy to add new hardware drivers
   - Good documentation complete with examples
   - Much more

---

INSTALLATION
============


#### DEPENDENCIES

Before you can create an instance and run Pytomation automation software you must satisfy a few dependencies. Pytomation is written in Python and is currently being tested well with version 3.6.x, on the Raspberry Pi and Amd64 architectures. There are also pre-built docker images (auto-built by Docker Hub) available at https://hub.docker.com/r/dheaps/pytomation/, or you can build a Docker image, with the Dockerfile.

Pytomation also requires the following packages to be installed for normal operation:
 
 - pySerial - Support for RS232 serial interfaces.
 - Pyephem - High-precision astronomy computations for sunrise/sunset.
 - Pytz - World timezone definitions.
 - APScheduler - Advanced Python Scheduler

Optional Packages:
 - python-gevent - A coroutine-based Python networking library (PytoWebSocketServer)
 - python-openssl - Allows the PytoWebSocketServer to use native SSL (https and wss connections)

Additional packages are required for development and testing. See `requirements.txt` for a more complete list.

Debian packages are available for pySerial, pytz, python-gevent, and python-openssl. They can be installed with : 

    sudo apt-get install git python-dev python-serial python-tz python-gevent python-openssl

For other operating systems, search your package manager for the equivalent packages or use pip to install the Python dependencies.

The remaining dependencies can be installed with `pip3`. Pip3 is a tool for installing and managing Python packages, such as those found in the Python Package Index.

Again, under Debian distributions you can install the python3-pip package: 

    sudo apt-get install python3-pip

Once pip is installed it is easy to install the rest of the dependencies with the following commands:

    sudo pip3 install pyephem 
    sudo pip3 install APScheduler

To use the optional websocket server:

    sudo pip3 install gevent-websocket

The gevent-websocket server is pretty fast, but can be accelerated further by installing wsaccel and ujson or simplejson

    sudo pip3 install wsaccel ujson
    
The other pip3 packages are listed in requirments.txt and are optional. They are only necessary to use the interface that, which uses that package. For Example, for Phillps Hue support, install the phue package.

#### Website encryption (SSL)
1) Utilize the scrit created by Dobes Vandermeer at https://gist.github.com/dobesv/13d4cb3cbd0fc4710fa55f89d1ef69be

2) Copy the cert and key files for the server cert (not the root CA) to the ssl folder (or /secured/ssl for docker) as server.crt and server.key

3) To import the root CA, on your client devices, so all your generated certificates work on your devices follow the steps from:
https://thomas-leister.de/en/how-to-import-ca-root-certificate/

4) To create a cert that can be imported into the android system, using root privelege (does not work with the latst android 11):
https://blog.jeroenhd.nl/article/android-7-nougat-and-certificate-authorities#howto-install

    ```
    openssl x509 -inform PEM -subject_hash_old -in /etc/ssl/certs/cacert.pem | head -1
    cat /etc/ssl/certs/cacert.pem > [outputFromFirstCommand].0
    openssl x509 -inform PEM -text -in /etc/ssl/certs/cacert.pem -out /dev/null >> [outputFromFirstCommand].0
    ```
    Example
    ```
    cat /etc/ssl/certs/cacert.pem > 5ed36f99.0
    openssl x509 -inform PEM -text -in /etc/ssl/certs/cacert.pem -out /dev/null >> 5ed36f99.0
    ```
    Resulting file must be copied to /system/etc/security/cacerts/ on android system.

5) For the latests Android you must secure your device with pin/patern/etc, copy to your sdcard with the .crt extension, and open it. Android will prompt you to import as a "user" cert. (you can no longer add system cert, unless you roll your own rom or use a Magisk trick.

6) For Firefox Mobile save the cert to your sdcard and browse to it in firefox like file:///storage/emulated/0. Once you click on your cert it will prompt you to import.

Build openzwave and python-openzwave
====================================
Aeon Labs Z-Wave requires python-openzwave, which  must be compiled from source. It's highly recommend you use the archived source code. Version 3.0+ no longer requires Cython, which was the source of most of the build/seg fault issues with python-openzwave. 3.0beta2 has been tested to work on both a 64bit Ubuntu 14.04 system and a Raspberry PI. Instructions are at https://github.com/OpenZWave/python-openzwave/blob/master/INSTALL_ARCH.txt.

The config for OpenZwave will be located in the extracted archive, at openzwave/config. I recommend copying the config to your system /etc:

    sudo cp -R openzwave/config /etc/openzwave
    sudo chown -R pyto:root /etc/openzwave
    sudo chmod 660 /etc/openzwave/options.xml

Also note that if you have any security devices in your Zwave network, you will need to set the NetworkKey option in options.xml. That network key is why it's recommend to change the file permissions on options.xml, so only root and the pyto user can read it. 

#### Permissions
Like with all other interfaces. Make sure the pyto user account owns or otherwise has permissions to use the device. You may want to give your own usr account access as well.

    sudo chown youruseraccount:pyto /dev/yourzwavestick
    sudo chmod 770 /dev/yourzwavestick

or

    sudo chown pyto:pyto /dev/yourzwavestick
    sudo chmod 770 /dev/yourzwavestick
    
#### Make Permissions Permanent 
Add the following either `/etc/udev/rules.d` or `/lib/udev/rules.d` (Similar procedure can be used for other serial interfaces. `lsusb -v` can grab the necessary ATTRS info.)

    SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", SYMLINK+="zwave", GROUP="pyto", OWNER="pyto"

#### ozwsh (OpenZWave Shell, for testing)

    sudo pip install urwid louie
    /ozwsh.sh --device=/dev/yourzwavestick

INSTALL
=======
You are now ready to install Pytomation. First, clone the Pytomation git repository. Change into the Pytomation repo directory and run `./install.sh`. You may have to make it executable with the command `chmod +x ./install.sh` first. Install.sh can take an optional argument which points to an alternate installation directory. If you chose that option, be sure to update /etc/init.d/pytomation with the correct installation directory:

     ./install.sh /some/other/folder/pytomation

The install.sh command does the following:
 
  - Confirms where you are installing Pytomation to.
  - Makes a "pyto" user and creates the home directory.
  - Copies all the necessary files into Pytomation's HOME.
  - Creates an /etc/init.d/pytomation init script for starting Pytomation on boot.
  - Configures pytomation to start automatically at boot time

You are now ready to configure pytomation and create an instance for your devices.

