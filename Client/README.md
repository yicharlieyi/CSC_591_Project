# Client

## Environment Settings
To run this client, ensure the following environment is set up:

### Requirements
- Python 3.8 or higher
- Internet access to connect to the remote MQTT broker

### Required Python Packages
Run the following in the terminal

```
pip install tabulate pytz paho-mqtt

```

## Run the Script
First, add the broker ip to line 13 of `sub.py`

Navigate to the repository where the `sub.py` resides and run the scri[t] with the following code to subscribe to the all the event topics and display the event status:  
- `python sub.py` 

After connecting, it will subscribe to the following topics:
```
/gate/entry/open
/gate/entry/close
/gate/exit/open
/gate/exit/close
vehicle/able_enter/request
vehicle/able_enter/response
vehicle/able_exit/request
vehicle/able_exit/response
vehicle/validate_entry/request
vehicle/validate_entry/response
vehicle/validate_exit/request
vehicle/validate_exit/response
billing/transactions
system/status
```

## Usage
Once connected, the client will:

- Display gate events (entry/exit opened/closed)

- Print vehicle entries and exits in real time

- Show billing receipts when received from the billing/transactions topic

- Output periodic system status updates (occupancy, capacity, system status, and timestamp)

### Commands
You can type any of the following commands at the prompt:

- `billing`: Displays a formatted table of all billing transactions

- `events`: Displays the last 10 system events

- `exit`: Stops the monitor and disconnects


## Sample Outputs
[2025-04-13 01:04:45] GATE: Exit gate opened 

=========================  
BILLING RECEIPT FOR VEHICLE ABC123 

Entry Time:    2025-04-13 01:04:38  
Exit Time:     2025-04-13 01:04:46  
Duration:      0:00:08  
Charge:        $2.00  
System Session: 2  
Vehicle Session: 2   
 

SYSTEM STATUS UPDATE [2025-04-13 01:04:48]  
Occupancy: 0/4  
Available: 4  
Status:    ONLINE  
Timestamp: 2025-04-13 01:04:48  
  
## API Documentation
https://pypi.org/project/paho-mqtt/#usage-and-api
