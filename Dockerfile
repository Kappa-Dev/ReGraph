############################################################
# Dockerfile to build Python WSGI Application Containers
# Based on Ubuntu
############################################################

# Set the base image to Ubuntu
FROM ylecornec/regraph_base

# File Author / Maintainer
MAINTAINER Le Cornec Yves-Stan

# Add the application resources URL
#RUN echo "deb http://archive.ubuntu.com/ubuntu/ $(lsb_release -sc) main universe" >> /etc/apt/sources.list

COPY . ReGraph
#RUN pip3 install -r ReGraph/requirements.txt

RUN git clone https://github.com/Kappa-Dev/RegraphGui.git
RUN ln -s ../RegraphGui ReGraph/RegraphGui

# Expose ports
EXPOSE 5000

# Set the default directory where CMD will execute
WORKDIR ReGraph

# Set the default command to execute    
# when creating a new container
# i.e. using CherryPy to serve the application
CMD python3 webserver.py
