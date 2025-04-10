# CSC_591
Repo for CSC 591 Final Project

# AWS EC2 Broker

We used an AWS EC2 Linux (Ubuntu 24.04) instance as the platform for our broker since it was very simple and easy to setup, confiugre, and run.

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
ssh -i project.pem ubuntu@98.81.192.91
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

## Run Logger
To capture the decisions being sent, we will use a python client. First install the requirements

~~~
sudo apt install python3-pip
pip install paho-mqtt
~~~

Run the script:
~~~
python3 mqtt_broker_logs.py
~~~

# Cloud Server (AWS EC2)
## Connection
- Open a terminal and navigate to the folder where the `project.pem` file is located.  
- Use the following command to connect:  
- `ssh -i project.pem ubuntu@98.81.192.91`

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
