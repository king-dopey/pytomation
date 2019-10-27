# Use latest Python runtime as parent image
FROM python:latest
#Add user
RUN useradd -m -d /home/pytomation pyto

#Copy App
WORKDIR /home/pytomation
ADD . /home/pytomation 
RUN chown -R pyto /home/pytomation
RUN mv /home/pytomation/pytomation/common/config_docker_default.py /home/pytomation/pytomation/common/config.py 

#Install system dependencies
RUN apt-get update
RUN apt-get -y install libudev-dev

#Install requirements
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

#link openzwave config to /etc
RUN ln -s /usr/local/lib/python3.8/site-packages/python_openzwave/ozw_config /etc/openzwave

#Expose 8080
EXPOSE 8080

#Run Pytomation
CMD ["./dockerentry.sh"]
