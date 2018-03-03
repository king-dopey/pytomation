#!/bin/bash
# Move contents of the secured mounted volume to the correct locations
# and give the only the pyto user read-only access to them

# Set local time based on environment variable given
if [ ! -z {$TZ+x} ]
then
	echo "Setting Timezone $TZ"
	echo $TZ > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
fi

# Change device permissions based on environment variable given
if [ ! -z {$DEVICES+x} ]
then
	IFS=';'
	read -ra DEVS <<< "$DEVICES"
	for dev in "${DEVS[@]}"; do
		echo "Setting Permission for device $dev"
	    chown pyto:pyto $dev
	done
fi

# Copy OpenZwave options.xml 
if [ -e /secured/config/openzwave.xml ]
then
	echo "Preparing OpenZwave options.xml"
	cp /secured/config/openzwave.xml /etc/openzwave/options.xml
	chown pyto:root /etc/openzwave/options.xml
	chmod 400 /etc/openzwave/options.xml
fi

# Copy Pytomation config.py
if [ -e /secured/config/config.py ]
then
	echo "Preparing Pytomation config.py"
	cp /secured/config/config.py /home/pytomation/pytomation/common
	chown pyto:root /home/pytomation/pytomation/common/config.py
	chmod 400 /home/pytomation/pytomation/common/config.py
fi

# Copy Instance files
if [ -d /secured/instances ]
then
	echo "Preparing Instance files"
	cp /secured/instances/* /home/pytomation/instances
	chown pyto:root /home/pytomation/instances/*
	chmod 400 /home/pytomation/instances/*
fi

# Copy SSL certificates
if [ -d /secured/ssl ]
then
	echo "Preparing SSL certificates"
	cp -R /secured/ssl /home/pytomation/ssl
	chown -R pyto:root /home/pytomation/ssl
	chmod 400 /home/pytomation/ssl/*
fi

# Now run Pytomation as the pyto user
exec su - pyto -c "python3 /home/pytomation/pytomation.py"