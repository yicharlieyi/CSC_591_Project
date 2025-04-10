import paho.mqtt.client as mqtt
from datetime import datetime
import json
from tabulate import tabulate
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# Configuration
BROKER_ADDRESS = "98.81.192.91"
CLIENT_ID = "ParkingMonitor"
TOPICS = [
    "vehicle/validate_entry/response",
    "vehicle/validate_exit/response",
    "gate/entry/open",
    "gate/entry/close",
    "gate/exit/open",
    "gate/exit/close",
    "billing/transactions",
    "system/status"
]

class ParkingMonitor:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                                client_id=CLIENT_ID, 
                                protocol=mqtt.MQTTv5)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Connect with will and session expiry
        properties = Properties(PacketTypes.CONNECT)
        properties.SessionExpiryInterval = 30 * 60  # 30 minutes
        
        self.client.connect(BROKER_ADDRESS, 
                          port=1883, 
                          clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                          properties=properties,
                          keepalive=60)
        
        self.client.loop_start()
        
        # Store billing records
        self.billing_records = {}
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"Connected to broker with result code {reason_code}")
        for topic in TOPICS:
            client.subscribe(topic, qos=2)
        print("Subscribed to all topics. Waiting for messages...\n")
    
    def on_message(self, client, userdata, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        topic = msg.topic
        payload = msg.payload.decode()
        
        try:
            if topic == "vehicle/validate_entry/response":
                vehicle_id = payload.split("|")[0] if "|" in payload else payload
                print(f"[{timestamp}] ENTRY: Vehicle {vehicle_id} entered parking lot")
                
            elif topic == "vehicle/validate_exit/response":
                vehicle_id = payload.split("|")[0] if "|" in payload else payload
                print(f"[{timestamp}] EXIT: Vehicle {vehicle_id} exited parking lot")
                
            elif topic == "gate/entry/open":
                print(f"[{timestamp}] GATE: Entry gate opened")
                
            elif topic == "gate/entry/close":
                print(f"[{timestamp}] GATE: Entry gate closed")
                
            elif topic == "gate/exit/open":
                print(f"[{timestamp}] GATE: Exit gate opened")
                
            elif topic == "gate/exit/close":
                print(f"[{timestamp}] GATE: Exit gate closed")
                
            elif topic == "billing/transactions":
                try:
                    data = json.loads(payload)
                    vehicle_id = data["uid"]
                    self.billing_records[vehicle_id] = data
                    
                    # Format duration for display
                    duration = data["duration"].split(".")[0]  # Remove microseconds
                    
                    print("\n" + "="*50)
                    print(f"BILLING RECEIPT FOR VEHICLE {vehicle_id}")
                    print("="*50)
                    print(f"Entry Time: {data['check_in']}")
                    print(f"Exit Time:  {data['check_out']}")
                    print(f"Duration:   {duration}")
                    print(f"Charge:     ${data['charge']:.2f}")
                    print("="*50 + "\n")
                    
                except json.JSONDecodeError:
                    print(f"[{timestamp}] BILLING: {payload}")
                    
            elif topic == "system/status":
                try:
                    status = json.loads(payload)
                    print(f"\nSYSTEM STATUS UPDATE [{timestamp}]")
                    print(f"Occupancy: {status['occupancy']}/{status['capacity']}")
                    print(f"Status: {status['status'].upper()}\n")
                except:
                    print(f"[{timestamp}] STATUS: {payload}")
                    
        except Exception as e:
            print(f"[{timestamp}] ERROR processing message: {str(e)}")
    
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        print(f"Disconnected from broker with result code {reason_code}")
    
    def display_billing_summary(self):
        print("\n" + "="*50)
        print("BILLING SUMMARY REPORT")
        print("="*50)
        
        if not self.billing_records:
            print("No billing records available")
            return
            
        table_data = []
        for vehicle_id, record in self.billing_records.items():
            duration = record["duration"].split(".")[0]  # Remove microseconds
            table_data.append([
                vehicle_id,
                record["check_in"],
                record["check_out"],
                duration,
                f"${float(record['charge']):.2f}"
            ])
        
        print(tabulate(table_data, 
                      headers=["Vehicle ID", "Entry Time", "Exit Time", "Duration", "Charge"],
                      tablefmt="grid"))
        print("="*50 + "\n")
    
    def cleanup(self):
        self.client.disconnect()
        self.client.loop_stop()

if __name__ == "__main__":
    try:
        monitor = ParkingMonitor()
        
        # Keep the program running
        while True:
            command = input("\nEnter 'summary' to show billing report or 'exit' to quit: ").strip().lower()
            
            if command == "summary":
                monitor.display_billing_summary()
            elif command == "exit":
                break
                
    except KeyboardInterrupt:
        print("\nShutting down monitor...")
    finally:
        monitor.cleanup()
        print("Monitor stopped.")