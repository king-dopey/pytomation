Running the Raspberry Pi Pytomation remote client.

The rpi_remote_client.py client will only run on versions of Python 3.4
or higher.


Setting GPIO pins
--------------------------
Please see the documentation for the Pytomation RpiGpioRemote interface for 
setting GPIO pins.  This client auto connects to your Pytomation instance and 
auto configures GPIO, from settings in your instance file.


Running on the Pi
--------------------------
You can choose to run the client manually or automatically on boot.

First make sure the rpi_remote_client.py file is executable.  
"sudo chmod +x rpi_remote_client.py"  will do the trick or use your favorite
file manager.

For manual run from the current directory, ./rpi_remote_client.py

For automatic run at boot, first make then /etc/rc.local file executable so it 
runs at boot.  Now add this line to your /etc/rc.local file:
  su pyto -c "sleep 20;/home/pyto/rpi_remote_client.py 1>/dev/null" &

This assumes you have a user "pyto" and the rpi_remote_client.py file 
is in the pyto user $HOME directory.  To run as the default "pi" user, change 
the line like this.
  su pi -c "sleep 20;/home/pi/rpi_remote_client.py 1>/dev/null" &


Settable parameters:
--------------------------
You must edit the "rpi_remote_client.py" file and change the following 
parameters before execution.


host=<string>       Host name or IP address of your Pytomation server.
port=<int>          IP port of your Pytomation server.
secret=<string>     Shared secret contained both here and on your server.  
                    This is a string that should be between 8 and 32 characters
                    in length and contains ascii printable characters.

sslcert=<string>    OPTIONAL: Path to an openssl cert for encrypting the link.
                    You do not require encryption.
If you want to use encryption you must generate a certificate|key pair for your
Pytomation server.  You can use the following command and I have provided an 
example run as well.

  openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key -nodes \
          -out selfsigned.cert -sha256 -days 1000

Your Pytomation server must have both the cert and key, the client only 
requires the cert file.

When generating a cert|key pair you should use the host name of your Pytomation
server.  Here is an example:

    $ openssl req -x509 -newkey rsa:2048 -keyout selfsigned.key -nodes \
           -out selfsigned.cert -sha256 -days 1000
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

