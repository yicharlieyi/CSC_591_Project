import paho.mqtt.client as mqtt
import time
import random
from datetime import datetime
import json
import threading

# Configuration
BROKER_ADDRESS = "44.204.193.8"  # Your EC2 instance IP
CLIENT_ID = "ParkingSimulator"
VEHICLE_IDS = ["ABC123", "XYZ789", "DEF456", "GHI789", "JKL012"]
SIMULATION_SPEED = 1  # Seconds between actions

# Topics (must match your cloud system)
TOPICS = {
    "able_enter_req": "vehicle/able_enter/request",
    "able_enter_resp": "vehicle/able_enter/response",
    "able_exit_req": "vehicle/able_exit/request",
    "able_exit_resp": "vehicle/able_exit/response",
    "validate_entry_req": "vehicle/validate_entry/request",
    "validate_entry_resp": "vehicle/validate_entry/response",
    "validate_exit_req": "vehicle/validate_exit/request",
    "validate_exit_resp": "vehicle/validate_exit/response",
    "entry_gate_open": "/gate/entry/open",
    "entry_gate_close": "/gate/entry/close",
    "exit_gate_open": "/gate/exit/open",
    "exit_gate_close": "/gate/exit/close",
    "billing": "billing/transactions",
    "status": "system/status"
}

class ParkingSimulator:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                                client_id=CLIENT_ID, 
                                protocol=mqtt.MQTTv5)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        self.vehicles_in_lot = set()
        self.lot_capacity = 4
        self.simulation_active = True
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected to broker")
            self.connected = True
            # Subscribe to response topics
            self.client.subscribe(TOPICS["able_enter_resp"], qos=2)
            self.client.subscribe(TOPICS["able_exit_resp"], qos=2)
            self.client.subscribe(TOPICS["validate_entry_resp"], qos=2)
            self.client.subscribe(TOPICS["validate_exit_resp"], qos=2)
        else:
            print(f"Connection failed with code {reason_code}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        print(f"Received on {msg.topic}: {msg.payload.decode()}")

    def connect(self):
        self.client.connect(BROKER_ADDRESS, port=1883, keepalive=60)
        self.client.loop_start()
        time.sleep(1)  # Wait for connection

    def simulate_vehicle_entry(self, vehicle_id):
        """Simulate a complete vehicle entry sequence"""
        print(f"\n=== Simulating ENTRY for vehicle {vehicle_id} ===")
        
        # Step 1: Send able_enter request
        self.client.publish(TOPICS["able_enter_req"], vehicle_id, qos=2)
        print(f"Sent able_enter request for {vehicle_id}")
        time.sleep(SIMULATION_SPEED)
        
        # Step 2: Open entry gate (would normally wait for response)
        self.client.publish(TOPICS["entry_gate_open"], "open", qos=2)
        print("Entry gate opened")
        time.sleep(SIMULATION_SPEED)
        
        # Step 3: Send validate_entry request
        self.client.publish(TOPICS["validate_entry_req"], vehicle_id, qos=2)
        print(f"Sent validate_entry for {vehicle_id}")
        time.sleep(SIMULATION_SPEED)
        
        # Step 4: Close entry gate
        self.client.publish(TOPICS["entry_gate_close"], "close", qos=2)
        print("Entry gate closed")
        
        self.vehicles_in_lot.add(vehicle_id)
        self.publish_system_status()
        print(f"=== Vehicle {vehicle_id} entered successfully ===\n")

    def simulate_vehicle_exit(self, vehicle_id):
        """Simulate a complete vehicle exit sequence"""
        print(f"\n=== Simulating EXIT for vehicle {vehicle_id} ===")
        
        # Step 1: Send able_exit request
        self.client.publish(TOPICS["able_exit_req"], vehicle_id, qos=2)
        print(f"Sent able_exit request for {vehicle_id}")
        time.sleep(SIMULATION_SPEED)
        
        # Step 2: Open exit gate (would normally wait for response)
        self.client.publish(TOPICS["exit_gate_open"], "open", qos=2)
        print("Exit gate opened")
        time.sleep(SIMULATION_SPEED)
        
        # Step 3: Send validate_exit request
        self.client.publish(TOPICS["validate_exit_req"], vehicle_id, qos=2)
        print(f"Sent validate_exit for {vehicle_id}")
        time.sleep(SIMULATION_SPEED)
        
        # Step 4: Generate billing record
        session = {
            "uid": vehicle_id,
            "check_in": datetime.now().isoformat(),
            "check_out": datetime.now().isoformat(),
            "duration": "0:30:00",
            "charge": 2.50,
            "system_session": random.randint(1000, 9999),
            "vehicle_session": random.randint(1, 10)
        }
        self.client.publish(TOPICS["billing"], json.dumps(session), qos=2)
        print("Billing record published")
        time.sleep(SIMULATION_SPEED)
        
        # Step 5: Close exit gate
        self.client.publish(TOPICS["exit_gate_close"], "close", qos=2)
        print("Exit gate closed")
        
        self.vehicles_in_lot.discard(vehicle_id)
        self.publish_system_status()
        print(f"=== Vehicle {vehicle_id} exited successfully ===\n")

    def publish_system_status(self):
        """Publish current system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "occupancy": len(self.vehicles_in_lot),
            "capacity": self.lot_capacity,
            "status": "online",
            "available": self.lot_capacity - len(self.vehicles_in_lot)
        }
        self.client.publish(TOPICS["status"], json.dumps(status), qos=2)
        print("Published system status update")

    def random_simulation(self):
        """Run continuous random simulation"""
        while self.simulation_active:
            action = random.choice(["entry", "exit"])
            
            if action == "entry" and len(self.vehicles_in_lot) < self.lot_capacity:
                vehicle_id = random.choice([v for v in VEHICLE_IDS if v not in self.vehicles_in_lot])
                self.simulate_vehicle_entry(vehicle_id)
            elif action == "exit" and self.vehicles_in_lot:
                vehicle_id = random.choice(list(self.vehicles_in_lot))
                self.simulate_vehicle_exit(vehicle_id)
            else:
                print("No valid action possible (lot full or empty)")
                
            time.sleep(random.uniform(1, 3))  # Random delay between actions

    def stop(self):
        """Stop the simulation"""
        self.simulation_active = False
        self.client.disconnect()
        self.client.loop_stop()

def interactive_simulation(simulator):
    """Run simulation with user input"""
    print("\nParking Lot Simulator - Interactive Mode")
    print("Commands: entry, exit, status, quit")
    
    while True:
        cmd = input("> ").strip().lower()
        
        if cmd == "entry":
            if len(simulator.vehicles_in_lot) >= simulator.lot_capacity:
                print("Parking lot is full!")
                continue
                
            print(f"Available vehicles: {[v for v in VEHICLE_IDS if v not in simulator.vehicles_in_lot]}")
            vehicle_id = input("Enter vehicle ID: ").strip().upper()
            if vehicle_id in VEHICLE_IDS and vehicle_id not in simulator.vehicles_in_lot:
                simulator.simulate_vehicle_entry(vehicle_id)
            else:
                print("Invalid vehicle ID")
                
        elif cmd == "exit":
            if not simulator.vehicles_in_lot:
                print("Parking lot is empty!")
                continue
                
            print(f"Vehicles in lot: {list(simulator.vehicles_in_lot)}")
            vehicle_id = input("Enter vehicle ID: ").strip().upper()
            if vehicle_id in simulator.vehicles_in_lot:
                simulator.simulate_vehicle_exit(vehicle_id)
            else:
                print("Invalid vehicle ID")
                
        elif cmd == "status":
            simulator.publish_system_status()
            
        elif cmd == "quit":
            break
            
        else:
            print("Invalid command")

if __name__ == "__main__":
    simulator = ParkingSimulator()
    simulator.connect()
    
    if not simulator.connected:
        print("Failed to connect to broker")
        exit(1)
    
    print("\nParking Lot Simulation Options:")
    print("1. Interactive simulation")
    print("2. Automated random simulation")
    print("3. Single entry-exit cycle")
    
    choice = input("Select mode (1-3): ").strip()
    
    try:
        if choice == "1":
            interactive_simulation(simulator)
        elif choice == "2":
            print("Starting random simulation... Press Ctrl+C to stop")
            simulator.random_simulation()
        elif choice == "3":
            vehicle_id = random.choice(VEHICLE_IDS)
            simulator.simulate_vehicle_entry(vehicle_id)
            time.sleep(2)
            simulator.simulate_vehicle_exit(vehicle_id)
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    finally:
        simulator.stop()
        print("Simulation ended")