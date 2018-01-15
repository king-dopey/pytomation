#!/bin/bash
# Move contents of the secured mounted volume to the correct locaitons
# and give the only the pyto user read-only access to them

# Copy OpenZwave options.xml 
if [ -e /secured/config/openzwave.xml ]
then
	cp /secured/config/openzwave.xml /etc/openzwave/options.xml
	chown pyto:root /etc/openzwave/options.xml
	chmod 400 /etc/openzwave/options.xml
fi

# Copy Pytomation config.py
if [ -e /secured/config/config.py ]
then
	cp /secured/config/config.py /home/pytomation/pytomation/common
	chown pyto:root /home/pytomation/pytomation/common/config.py
	chmod 400 /home/pytomation/pytomation/common/config.py
fi

# Copy Instance files
if [ -d /secured/instances ]
then
	cp /secured/instances/* /home/pytomation/instances
	chown pyto:root /home/pytomation/instances/*
	chmod 400 /home/pytomation/instances/*
fi

# Copy SSL certificates
if [ -d /secured/ssl ]
then
	cp -R /secured/ssl /home/pytomation/ssl
	chown -R pyto:root /home/pytomation/ssl
	chmod 400 /home/pytomation/ssl/*
fi

# Now run Pytomation as the pyto user
exec su - pyto -c "python3 /home/pytomation/pytomation.py"