# Parking Lot Simulator
The Parking Lot Simulator is a Python-based MQTT client that simulates vehicle entry and exit, gate operations, and parking validation requests within a smart parking system. It interacts with a central broker to mimic real-world behavior in a controlled test environment.

## Environment Settings
To run this simulator, ensure the following environment is set up:

### Requirements
- Python 3.8 or higher
- MQTT broker (e.g., public broker or EC2-hosted broker)

### Required Python Packages
Run the following in the terminal

`pip install pytz paho-mqtt`

## Run the Script
First, make sure the MQTT broker is running and accessible, and add the broker ip to line 9 of `cloud_mqtt_client.py`

Navigate to the repository where the `cloud_mqtt_client.py` resides and run the script with the following code:
`python cloud_mqtt_client.py` 

Use the command-line interface to simulate various actions

## Usage

### Example Simulation Flow
1. Request to enter:  
Publish to `vehicle/able_enter/request` with vehicle ID.

2. If response is "true" on `vehicle/able_enter/response`, publish to:

    - `vehicle/validate_entry/request`

    - `/gate/entry/open`

     - `/gate/entry/close`

3. Repeat similar flow for exits using `able_exit` and `validate_exit`.

## API Documentation
https://pypi.org/project/paho-mqtt/#usage-and-api
