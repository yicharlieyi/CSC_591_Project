# CSC_591
Repo for CSC 591 Final Project

# AWS EC2 Broker

We used an AWS EC2 Linux (Ubuntu 22.04) instance as the platform for our broker since it was very simple and easy to setup, confiugre, and run.

NOTE: All commands should be run a terminal

## Setup
Go onto the AWS Console and setup an EC2 instance with the following stats
- Ubuntu22.04
- Allow HTTP/HTTPS traffic
- t2.micro
- 8GB storage

Create a key pair so you can ssh into it. Make sure to save the key file

Launch the instance. Go into the security settings and click on the inbound rules group. Click edit group. Add a rule to allow the mqtt clients to connect (can specifically add their IPs or just allow all - which is not advised as it is unsafe).

Start the instance.

## SSH In

Go to where you key file is. Run the following command:
```
chmod 400 KEY_FILE_NAME
```

Then ssh via the following command:
```
ssh -i KEY_FILE_NAME ubuntu@EC2_IP
ssh -i cloud.pem ubuntu@52.91.167.82
```

## Installation

Run the following to download mosquitto  

```
sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
sudo apt-get update
sudo apt-get install mosquitto
```  

Now mosquitto should be downloaded and probably is running. We want to stop the default service and configure our own. So run  

```
sudo systemctl stop mosquitto
```  


## Setup
### Config File
A default config file needs to be made to enable clients to connect. We will go with a simple setup and not require any authentication.

First, make a new config file in the mosquitto config directory: 

```
touch 592_mqtt.conf
```  

Paste the contents of the `592_mqtt.conf` file the into the file just created. This allows any ip to connect without any authentication as well as logs everything in human readable format.

### Firewall
Linux needs to allow the port to be accessed, which can be done by changing the firewall rules.

```
sudo ufw allow 1883 
sudo ufw enable
```


## Run Broker
### Start Broker:

Run the following. You should see logs being printed in real time.

```
mosquitto -v -c 592_mqtt.conf
``` 

Since mosquitto will not print the contents of the messages, we need to run it in the background

```
mosquitto -c 592_mqtt.conf -d
``` 

### Stop Broker:
To stop the broker, just press `CTLR + C` in the same terminal you started it in.

# Run Cloud System
To run the cloud system. First install the requirements in the same EC2 instance the broker is running on:

~~~
sudo apt install python3-pip
pip install tabulate paho-mqtt
~~~

Make the cloud system script:
```
touch cloud_system.py
```  

Paste the contents of the `cloud_system.py` file the into the file just created. 

Run the script:
```
python3 cloud_system.py
```
Cloud system should show connection success and topic subscription message.

# Client
- On the client device, you just need to pip install the library.
- `pip install tabulate paho-mqtt`  
- Run the client with the following code to subscribe to the all the event topics and display the event status:  
- `python sub.py` 


## API Documentation
https://pypi.org/project/paho-mqtt/#usage-and-api
