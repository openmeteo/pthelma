FROM ubuntu:16.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# Update && Upgrade os
RUN apt-get update
RUN apt-get -y upgrade

# Install essential libs
RUN apt-get -y install wget python3-pip python3-numpy python3-gdal
RUN apt-get -y install build-essential


# Install Dickinson
# https://github.com/openmeteo/dickinson
RUN wget https://github.com/openmeteo/dickinson/archive/0.2.1.tar.gz
RUN tar xzf 0.2.1.tar.gz
WORKDIR dickinson-0.2.1
RUN ./configure
RUN make
RUN make install
RUN ldconfig

# Create a working directory and install local pthlema
RUN mkdir /code
WORKDIR /code
COPY . /code/
RUN pip3 install .
