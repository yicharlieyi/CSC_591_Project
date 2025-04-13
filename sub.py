import paho.mqtt.client as mqtt
from datetime import datetime
import json
from tabulate import tabulate
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
import time
import sys
from collections import deque
import pytz

# Configuration
BROKER_ADDRESS = "44.204.193.8"  # EC2 instance IP
CLIENT_ID = "ParkingMonitor"
TOPICS = [
    "/gate/entry/open",
    "/gate/entry/close",
    "/gate/exit/open",
    "/gate/exit/close",
    "vehicle/able_enter/request",
    "vehicle/able_enter/response",
    "vehicle/able_exit/request",
    "vehicle/able_exit/response",
    "vehicle/validate_entry/request",
    "vehicle/validate_entry/response",
    "vehicle/validate_exit/request",
    "vehicle/validate_exit/response",
    "billing/transactions",
    "system/status"
]

class ParkingMonitor:
    def __init__(self):
        self.connected = False
        self.billing_records = {}
        self.recent_events = deque(maxlen=100)
        self.current_status = {
            "occupancy": 0,
            "capacity": 0,
            "status": "unknown",
            "timestamp": ""
        }
        self.vehicle_tracker = {}
        
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                                    client_id=CLIENT_ID, 
                                    protocol=mqtt.MQTTv5)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            properties = Properties(PacketTypes.CONNECT)
            properties.SessionExpiryInterval = 30 * 60

            print(f"Attempting to connect to broker at {BROKER_ADDRESS}...")
            self.client.connect(BROKER_ADDRESS, 
                              port=1883, 
                              clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                              properties=properties,
                              keepalive=60)
            
            self.client.loop_start()
            
            for _ in range(5):
                if self.connected:
                    break
                time.sleep(1)
            
            if not self.connected:
                raise ConnectionError("Failed to connect to MQTT broker")
                
        except Exception as e:
            print(f"Initialization error: {str(e)}")
            self.cleanup()
            raise

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"Successfully connected to broker")
            self.connected = True
            for topic in TOPICS:
                client.subscribe(topic, qos=2)
            print("Subscribed to all topics. Waiting for messages...\n")
        else:
            print(f"Connection failed with reason code: {reason_code}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        timestamp = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S")
        topic = msg.topic
        payload = msg.payload.decode()
        
        try:
            if topic in ["vehicle/able_enter/request", "vehicle/validate_entry/request"]:
                self.vehicle_tracker[payload] = {
                    "type": "entry",
                    "timestamp": timestamp,
                    "status": "pending"
                }
                return
            elif topic in ["vehicle/able_exit/request", "vehicle/validate_exit/request"]:
                self.vehicle_tracker[payload] = {
                    "type": "exit",
                    "timestamp": timestamp,
                    "status": "pending"
                }
                return
                
            vehicle_id = None
            if topic in ["vehicle/validate_entry/response", "vehicle/validate_exit/response"]:
                action_type = "entry" if "entry" in topic else "exit"
                vehicle_id = self._find_matching_vehicle(timestamp, action_type)
                
            event = {
                "timestamp": timestamp,
                "topic": topic,
                "payload": payload,
                "vehicle_id": vehicle_id,
                "display": self._format_event(topic, payload, timestamp, vehicle_id)
            }
            self.recent_events.append(event)
            
            if topic == "vehicle/validate_entry/response":
                if vehicle_id:
                    print(f"[{timestamp}] ENTRY: Vehicle {vehicle_id} entered parking lot")
                    if vehicle_id in self.vehicle_tracker:
                        self.vehicle_tracker[vehicle_id]["status"] = "completed"
                else:
                    print(f"[{timestamp}] ENTRY: Unknown vehicle entered")
                    
            elif topic == "vehicle/validate_exit/response":
                if vehicle_id:
                    print(f"[{timestamp}] EXIT: Vehicle {vehicle_id} exited parking lot")
                    if vehicle_id in self.vehicle_tracker:
                        self.vehicle_tracker[vehicle_id]["status"] = "completed"
                else:
                    print(f"[{timestamp}] EXIT: Unknown vehicle exited")
                    
            elif topic in ["/gate/entry/open", "/gate/entry/close", 
                          "/gate/exit/open", "/gate/exit/close"]:
                gate = "Entry" if "entry" in topic else "Exit"
                action = "opened" if "open" in topic else "closed"
                print(f"[{timestamp}] GATE: {gate} gate {action}")
                
            elif topic == "billing/transactions":
                self._process_billing(payload, timestamp)
                
            elif topic == "system/status":
                self._process_system_status(payload, timestamp)
                
        except Exception as e:
            error_msg = f"[{timestamp}] ERROR processing message: {str(e)}"
            print(error_msg)
            self.recent_events.append({
                "timestamp": timestamp,
                "topic": "error",
                "payload": error_msg,
                "display": error_msg
            })
    
    def _find_matching_vehicle(self, current_timestamp, action_type):
        current_time = datetime.strptime(current_timestamp, "%Y-%m-%d %H:%M:%S")
        candidates = {
            vid: data for vid, data in self.vehicle_tracker.items()
            if data["type"] == action_type and data["status"] == "pending"
        }
        
        if not candidates:
            return None
            
        most_recent = None
        min_diff = float('inf')
        
        for vid, data in candidates.items():
            event_time = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
            time_diff = (current_time - event_time).total_seconds()
            
            if 0 <= time_diff < min_diff:
                most_recent = vid
                min_diff = time_diff
                
        return most_recent
    
    def _format_timestamp(self, iso_timestamp):
        if "T" in iso_timestamp:
            try:
                dt = datetime.fromisoformat(iso_timestamp.replace("Z", ""))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                return iso_timestamp
        return iso_timestamp
    
    def _format_event(self, topic, payload, timestamp, vehicle_id=None):
        if topic == "vehicle/validate_entry/response":
            vid = vehicle_id or "Unknown"
            return f"[{timestamp}] Vehicle {vid} entered parking lot"
        elif topic == "vehicle/validate_exit/response":
            vid = vehicle_id or "Unknown"
            return f"[{timestamp}] Vehicle {vid} exited parking lot"
        elif topic == "/gate/entry/open":
            return f"[{timestamp}] Entry gate opened"
        elif topic == "/gate/entry/close":
            return f"[{timestamp}] Entry gate closed"
        elif topic == "/gate/exit/open":
            return f"[{timestamp}] Exit gate opened"
        elif topic == "/gate/exit/close":
            return f"[{timestamp}] Exit gate closed"
        elif topic == "billing/transactions":
            try:
                data = json.loads(payload)
                return f"[{timestamp}] Billing: Vehicle {data['uid']} charged ${data['charge']:.2f}"
            except:
                return f"[{timestamp}] Billing: {payload}"
        elif topic == "system/status":
            try:
                status = json.loads(payload)
                status['timestamp'] = self._format_timestamp(status['timestamp'])
                return f"[{timestamp}] Status: {status['occupancy']}/{status['capacity']} spots occupied"
            except:
                return f"[{timestamp}] Status: {payload}"
        return f"[{timestamp}] {topic}: {payload}"
    
    def _process_billing(self, payload, timestamp):
        """Process billing transaction messages with duplicate detection"""
        try:
            data = json.loads(payload)
            vehicle_id = data["uid"]
            
            # Duplicate detection
            if vehicle_id in self.billing_records:
                existing = self.billing_records[vehicle_id]
                if (existing["check_out"] == data["check_out"] and 
                    abs(float(existing["charge"]) - float(data["charge"])) < 0.01):
                    print(f"[{timestamp}] Duplicate billing record for {vehicle_id} - ignoring")
                    return
            
            self.billing_records[vehicle_id] = data
            
            data['check_in'] = self._format_timestamp(data['check_in'])
            data['check_out'] = self._format_timestamp(data['check_out'])
            duration = data["duration"].split(".")[0] if "." in data["duration"] else data["duration"]
            
            print("\n" + "="*50)
            print(f"BILLING RECEIPT FOR VEHICLE {vehicle_id}")
            print("="*50)
            print(f"Entry Time:    {data['check_in']}")
            print(f"Exit Time:     {data['check_out']}")
            print(f"Duration:      {duration}")
            print(f"Charge:        ${float(data['charge']):.2f}")
            print(f"System Session: {data.get('system_session', 'N/A')}")
            print(f"Vehicle Session: {data.get('vehicle_session', 'N/A')}")
            print("="*50 + "\n")
            
        except json.JSONDecodeError:
            print(f"[{timestamp}] BILLING: Invalid JSON - {payload}")
        except Exception as e:
            print(f"[{timestamp}] BILLING ERROR: {str(e)}")
    
    def _process_system_status(self, payload, timestamp):
        try:
            status = json.loads(payload)
            self.current_status = status
            status['timestamp'] = self._format_timestamp(status['timestamp'])
            
            print(f"\nSYSTEM STATUS UPDATE [{timestamp}]")
            print(f"Occupancy: {status['occupancy']}/{status['capacity']}")
            print(f"Available: {status.get('available', status['capacity'] - status['occupancy'])}")
            print(f"Status:    {status['status'].upper()}")
            print(f"Timestamp: {status['timestamp']}\n")
        except json.JSONDecodeError:
            print(f"[{timestamp}] STATUS: Invalid JSON - {payload}")
        except Exception as e:
            print(f"[{timestamp}] STATUS ERROR: {str(e)}")
    
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        print(f"Disconnected from broker with reason code: {reason_code}")
        self.connected = False
    
    def display_billing_summary(self):
        print("\n" + "="*50)
        print("BILLING SUMMARY REPORT")
        print("="*50)
        
        if not self.billing_records:
            print("No billing records available")
            return
            
        table_data = []
        for vehicle_id, record in self.billing_records.items():
            record['check_in'] = self._format_timestamp(record['check_in'])
            record['check_out'] = self._format_timestamp(record['check_out'])
            duration = record["duration"].split(".")[0] if "." in record["duration"] else record["duration"]
            table_data.append([
                vehicle_id,
                record["check_in"],
                record["check_out"],
                duration,
                f"${float(record['charge']):.2f}",
                record.get('system_session', 'N/A'),
                record.get('vehicle_session', 'N/A')
            ])
        
        print(tabulate(table_data, 
                      headers=["Vehicle ID", "Entry Time", "Exit Time", "Duration", "Charge", "System Session", "Vehicle Session"],
                      tablefmt="grid"))
        print("="*50 + "\n")
    
    def display_recent_events(self, count=10):
        print("\n" + "="*50)
        print(f"LAST {count} SYSTEM EVENTS")
        print("="*50)
        
        if not self.recent_events:
            print("No events recorded")
            return
            
        for event in list(self.recent_events)[-count:]:
            print(event["display"])
        print("="*50 + "\n")
    
    def cleanup(self):
        try:
            if hasattr(self, 'client'):
                self.client.disconnect()
                self.client.loop_stop()
                print("MQTT client disconnected")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    monitor = None
    try:
        monitor = ParkingMonitor()
        
        while True:
            if not monitor.connected:
                print("Connection lost. Attempting to reconnect...")
                monitor.cleanup()
                monitor = ParkingMonitor()
                
            command = input("\nCommands: [billing, events, exit]: \n").strip().lower()
            
            if command == "billing":
                monitor.display_billing_summary()
            elif command == "events":
                monitor.display_recent_events()
            elif command == "exit":
                break
            else:
                print("Invalid command. Try 'billing', 'events', or 'exit'")
                
    except KeyboardInterrupt:
        print("\nShutting down monitor...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if monitor:
            monitor.cleanup()
        print("Monitor stopped.")
        sys.exit(0)