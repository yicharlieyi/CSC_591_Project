# ECE_592_MQTT
Repo for CSC 591 Final Project

1. This project implements an IoT-based system to monitor the status of a door (open/close) using an Inertial Measurement Unit (IMU), a cloud-based classification algorithm, and MQTT for communication. The system consists of:

2. An IMU sensor attached to a door.

3. A Flask API running on AWS EC2 to classify door states and publish results via MQTT.

4. An MQTT client on a laptop to subscribe to the door status topic and display the current state.
# Broker

## Installation

Linux: 
```
sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
sudo apt-get update
sudo apt-get install mosquitto
``` 
MAC: `brew install mosquitto`  
Windows: Download from https://mosquitto.org/download/ and read README-windows.md  

## Setup
### Config File
Make a default config file and add a username and password if desired, or just allow anonymous connection. The 592_mqtt.conf file is a working example.

- For Linux, it goes in `/etc/mosquitto/conf.d`
- Mac/Windows: Specify the path to the config file when starting the broker.

### Firewall
You need to allow the port to be accessed. In Linux simply do the following:

```
sudo ufw allow 1883 
sudo ufw enable
```


### Start Broker:
`mosquitto -v -c /PATH_TO_CONFIG`

In Linux: `mosquitto -v -c /etc/mosquitto/conf.d/592.conf`

Alternatively:  
Linux: `sudo systemctl start mosquitto`  
Mac: `brew services start mosquitto`  
Windows: `net start mosquitto`  

### Stop Broker:
Linux: `sudo systemctl stop mosquitto`  
Mac: `brew services stop mosquitto`  
Windows: `net stop mosquitto`  

# Cloud Server (AWS EC2)
## Connection
- Open a terminal and navigate to the folder where the `hw3.pem` file is located.  
- Use the following command to connect:  
- `ssh -i hw3.pem ubuntu@3.145.84.19`

- Once connected to the EC2 instance, navigate to the folder where `app.py` is located:
- `cd /home/ubuntu`
- Then run the Flask app:
- `python3 app.py`
- The Flask app should be running, receiving raw data sent from IoT device, running classification algorithm, and sending classification decisions.

### Error
- In case of error, update the install dependencies:
```
sudo apt update
sudo apt install python3 python3-pip
pip3 install flask paho-mqtt
```

# Client
- On the client device, you just need to pip install the library.
- `pip install paho-mqtt`  
- Run the client with the following code to subscribe to the door/status topic and display the door status:  
- `python laptop.py` 


## API Documentation
https://pypi.org/project/paho-mqtt/#usage-and-api
