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
RUN apt-get -y install apt-utils 
RUN dpkg --configure -a
RUN apt-get upgrade -y
RUN apt-get -y install libudev-dev

#Install requirements
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

#Expose 8080
EXPOSE 8080

#Run Pytomation
CMD ["su", "-", "pyto", "-c", "python3", "/home/pytomation/pytomation.py"]