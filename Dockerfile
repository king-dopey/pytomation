# Use latest ubuntu OS as parent image
FROM ubuntu:latest
##########################################################################################
#Add user
RUN useradd -m -d /home/pytomation pyto
##########################################################################################
#Copy App
WORKDIR /home/pytomation
ADD . /home/pytomation 
RUN chown -R pyto /home/pytomation
RUN mv /home/pytomation/pytomation/common/config_docker_default.py /home/pytomation/pytomation/common/config.py 
##########################################################################################
#Install system dependencies
RUN apt-get update && \
apt-get dist-upgrade -y && \
apt-get -y install libudev-dev \
	python3-minimal \
	python3-pip \
	libbz2-dev \
	libssl-dev \
	libudev-dev \
	libyaml-dev \
	make \
	git \
	wget \
	zlib1g-dev \
	libmicrohttpd-dev \
	gnutls-bin \
	libgnutls28-dev && \
##########################################################################################
#Install OpenZWave Separately
pip3 install 'PyDispatcher>=2.0.5' six 'urwid>=1.1.1' pyserial && \
pip3 install python_openzwave --install-option="--flavor=git" && \
##########################################################################################
#Install requirements
pip3 install --trusted-host pypi.python.org -r requirements.txt && \
##########################################################################################
# clean up
apt-get -y remove python3-pip \
	libbz2-dev \
	libssl-dev \
	libudev-dev \
	libyaml-dev \
	make \
	git \
	wget \
	zlib1g-dev \
	libmicrohttpd-dev \
	gnutls-bin \
	libgnutls28-dev \
	python3-dev \
	g++ \
	cpp \
	gcc \
	build-essential && \
apt-get autoremove -y && \
apt-get clean && \
rm -rf /tmp/* /var/tmp/* /root/.cache/* \
/usr/share/man /usr/share/groff /usr/share/info \
/usr/share/lintian /usr/share/linda /var/cache/man && \
(( find /usr/share/doc -depth -type f ! -name copyright|xargs rm || true )) && \
(( find /usr/share/doc -empty|xargs rmdir || true ))
##########################################################################################
#link openzwave config to /etc
RUN ln -s /usr/local/lib/python$(python3 --version | tail -c +8 | head -c 3)/site-packages/python_openzwave/ozw_config /etc/openzwave
##########################################################################################
#Expose 8080
EXPOSE 8080
##########################################################################################
#Run Pytomation
CMD ["./dockerentry.sh"]
