import time
import logging
from tabulate import tabulate
from datetime import datetime
import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
import json
import math

# Topic configuration
topics = {
    "entry_gate_open":          "/gate/entry/open",
    "entry_gate_close":         "/gate/entry/close",
    "exit_gate_open":           "/gate/exit/open",
    "exit_gate_close":          "/gate/exit/close",
    "validate_able_enter_req":  "vehicle/able_enter/request",
    "validate_able_enter_resp": "vehicle/able_enter/response",
    "validate_able_exit_req":   "vehicle/able_exit/request",
    "validate_able_exit_resp":  "vehicle/able_exit/response",
    "validate_entry_req":       "vehicle/validate_entry/request",
    "validate_entry_resp":      "vehicle/validate_entry/response",
    "validate_exit_req":        "vehicle/validate_exit/request",
    "validate_exit_resp":       "vehicle/validate_exit/response",
    "billing_transactions":     "billing/transactions",  # New billing topic
    "system_status":            "system/status"          # New system status topic
}

vehicles = {}

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

# Status constants
OUT_LOT = 0
CHECKING_IN = 1
IN_LOT = 2
CHECKING_OUT = 3

# System parameters
LOT_CAPACITY = 4
WAIT_PERIOD = 30  # seconds
HOURLY_RATE = 2.00  # $2 per hour
FRACTIONAL_RATE = 1.00  # $1 per additional 30 minutes

class Vehicle:
    def __init__(self, uid):
        self.uid = uid
        self.attempt_check_ins = []
        self.attempt_check_outs = []
        self.check_ins = []
        self.check_outs = []
        self.sessions = []
        self.state = OUT_LOT
        self.vehicle_session = 0
        self.system_session = 0
    
    def check_in(self, system_session, timestamp=None):
        if not timestamp:
            timestamp = datetime.now()

        self.check_ins.append(timestamp)
        self.vehicle_session += 1
        self.system_session = system_session
        self.state = IN_LOT
        return timestamp

    def check_out(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.now()
        if not self.check_ins:
            raise ValueError("No check-in recorded for vehicle")
            
        check_in_timestamp = self.check_ins[-1]
        self.check_outs.append(timestamp)

        duration = timestamp - check_in_timestamp
        session = {
            "system_session_id": self.system_session,
            "vehicle_session_id": self.vehicle_session,
            "check_in": check_in_timestamp,
            "check_out": timestamp,
            "duration": duration
        }
        self.sessions.append(session)
        self.state = OUT_LOT
        return session

    def able_check_in(self):
        now = datetime.now()
        self.attempt_check_ins.append(now)

        # Check for rapid retries
        if (len(self.attempt_check_ins) >= 2 and 
            (now - self.attempt_check_ins[-2]).total_seconds() < WAIT_PERIOD):
            return False
        
        return self.state == OUT_LOT
        
    def able_check_out(self):
        now = datetime.now()
        self.attempt_check_outs.append(now)

        # Check for rapid retries
        if (len(self.attempt_check_outs) >= 2 and 
            (now - self.attempt_check_outs[-2]).total_seconds() < WAIT_PERIOD):
            return False
        
        return self.state == IN_LOT

class CloudSystem:
    def __init__(self, broker_ip, status_topic, client_id, default_topic="/", default_qos=2):
        self.broker_ip = broker_ip
        self.status_topic = status_topic
        self.default_topic = default_topic
        self.default_qos = default_qos
        self.client_id = client_id
        self.connected = False

        self._initialize_mqtt_client()
        self.system_session = 0
        self.current_occupancy = 0
        self.last_processed_messages = {}  # Track processed messages

    def _initialize_mqtt_client(self):
        """Initialize and connect the MQTT client"""
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=self.client_id, 
            protocol=mqtt.MQTTv5
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(self.status_topic, "offline", qos=2, retain=True)
        
        properties = Properties(PacketTypes.CONNECT)
        properties.SessionExpiryInterval = 2 * 60  # 2 minutes
        
        try:
            result = self.client.connect(
                self.broker_ip,
                port=1883,
                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                properties=properties,
                keepalive=60
            )
            if result != 0:
                raise ConnectionError(f"MQTT connection failed with code {result}")
            
            self.client.loop_start()
            # Wait for connection to establish
            for _ in range(5):
                if self.connected:
                    break
                time.sleep(1)
            
            if not self.connected:
                raise TimeoutError("MQTT connection timeout")
                
        except Exception as e:
            logging.error(f"Failed to initialize MQTT client: {str(e)}")
            self.cleanup()
            raise

    def calculate_charge(self, duration):
        """Calculate parking fee based on duration"""
        total_seconds = duration.total_seconds()
        hours = total_seconds / 3600
        
        if hours <= 1:
            return HOURLY_RATE
        else:
            additional_half_hours = math.ceil((hours - 1) * 2)
            return HOURLY_RATE + additional_half_hours * FRACTIONAL_RATE

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection events"""
        if reason_code == 0:
            self.connected = True
            logging.info("Successfully connected to MQTT broker")
            client.publish(self.status_topic, "online", qos=self.default_qos, retain=True)
            
            # Subscribe to all topics
            for topic in topics.values():
                client.subscribe(topic, qos=self.default_qos)
                logging.info(f"Subscribed to topic: {topic}")
        else:
            logging.error(f"Connection failed with reason code: {reason_code}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            payload = msg.payload.decode()
            topic = msg.topic

            # Create a message fingerprint for deduplication
            message_fingerprint = f"{topic}:{payload}"
            # Skip if we've recently processed this exact message
            if message_fingerprint in self.last_processed_messages:
                if (datetime.now() - self.last_processed_messages[message_fingerprint]).total_seconds() < 30:
                    logging.debug(f"Skipping duplicate message on {topic}")
                    return
            
            self.last_processed_messages[message_fingerprint] = datetime.now()
            
            # Clean up old entries
            self._cleanup_message_cache()

            logging.info(f"Received message on {topic}: {payload}")

            if topic == topics["validate_able_enter_req"]:
                self._handle_able_enter(payload)
            elif topic == topics["validate_able_exit_req"]:
                self._handle_able_exit(payload)
            elif topic == topics["validate_entry_req"]:
                self._handle_entry(payload)
            elif topic == topics["validate_exit_req"]:
                self._handle_exit(payload)
            else:
                logging.info(f"Received message on {topic}: {payload}")

        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")

    def _cleanup_message_cache(self):
        """Remove old entries from the message cache"""
        now = datetime.now()
        to_delete = []
        for fingerprint, timestamp in self.last_processed_messages.items():
            if (now - timestamp).total_seconds() > 300:  # 5 minute cache
                to_delete.append(fingerprint)
        for fingerprint in to_delete:
            del self.last_processed_messages[fingerprint]

    def _handle_able_enter(self, uid):
        """Handle vehicle entry validation request"""
        vehicle = vehicles.get(uid)
        if not vehicle:
            vehicle = Vehicle(uid)
            vehicles[uid] = vehicle

        if self.current_occupancy >= LOT_CAPACITY:
            response = "false"
            logging.info(f"Lot full - rejecting vehicle {uid}")
        elif vehicle.able_check_in():
            response = "true"
            logging.info(f"Vehicle {uid} validated for entry")
        else:
            response = "false"
            logging.info(f"Vehicle {uid} not ready for entry")

        self.publish(response, topics['validate_able_enter_resp'])

    def _handle_able_exit(self, uid):
        """Handle vehicle exit validation request"""
        vehicle = vehicles.get(uid)
        if not vehicle:
            response = "false"
            logging.warning(f"Unknown vehicle {uid} attempting to exit")
        elif vehicle.able_check_out():
            response = "true"
            logging.info(f"Vehicle {uid} validated for exit")
        else:
            response = "false"
            logging.info(f"Vehicle {uid} not ready for exit")

        self.publish(response, topics['validate_able_exit_resp'])

    def _handle_entry(self, uid):
        """Handle vehicle entry confirmation"""
        self.system_session += 1
        self.current_occupancy += 1
        vehicle = vehicles.get(uid)
        check_in_time = vehicle.check_in(self.system_session)
        
        # Publish system status update
        self._publish_system_status()
        
        # Publish entry confirmation
        self.publish("true", topics['validate_entry_resp'])
        logging.info(f"Vehicle {uid} entered at {check_in_time}")

    def _handle_exit(self, uid):
        """Handle vehicle exit confirmation"""
        vehicle = vehicles.get(uid)
        if not vehicle:
            logging.error(f"Exit request for unknown vehicle {uid}")
            return
        
        # Check if this vehicle is already in the process of exiting
        if vehicle.state != IN_LOT:
            logging.warning(f"Duplicate exit request for vehicle {uid}")
            return
        
        session = vehicle.check_out()
        self.current_occupancy -= 1
        
        # Calculate charge
        charge = self.calculate_charge(session["duration"])
        
        # Prepare billing record
        billing_record = {
            "uid": uid,
            "check_in": session["check_in"].isoformat(),
            "check_out": session["check_out"].isoformat(),
            "duration": str(session["duration"]),
            "charge": charge,
            "system_session": session["system_session_id"],
            "vehicle_session": session["vehicle_session_id"]
        }
        
        # Publish billing information
        self.publish(json.dumps(billing_record), topics["billing_transactions"])
        
        # Publish system status update
        self._publish_system_status()
        
        # Publish exit confirmation
        self.publish("true", topics['validate_exit_resp'])
        
        logging.info(f"Vehicle {uid} exited. Billing: ${charge:.2f}")

    def _publish_system_status(self):
        """Publish current system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "occupancy": self.current_occupancy,
            "capacity": LOT_CAPACITY,
            "status": "online",
            "available": LOT_CAPACITY - self.current_occupancy
        }
        self.publish(json.dumps(status), topics["system_status"])

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT disconnection"""
        self.connected = False
        logging.warning(f"Disconnected from broker. Reason: {reason_code}")
        
        # Attempt to reconnect
        try:
            client.reconnect()
        except Exception as e:
            logging.error(f"Reconnection failed: {str(e)}")

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'client'):
                # Publish offline status
                self.publish("offline", self.status_topic, retain=True)
                
                # Disconnect properly
                self.client.disconnect()
                self.client.loop_stop()
                logging.info("MQTT client stopped")
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")

    def publish(self, value, topic=None, retain=False):
        """Publish a message to MQTT"""
        if not self.connected:
            logging.warning("Not connected to broker - message not published")
            return
            
        if topic is None:
            topic = self.default_topic
            
        try:
            info = self.client.publish(topic, value, qos=self.default_qos, retain=retain)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"Failed to publish to {topic}: {info.rc}")
        except Exception as e:
            logging.error(f"Error publishing to {topic}: {str(e)}")

    def __del__(self):
        """Destructor for cleanup"""
        self.cleanup()

if __name__ == "__main__":
    try:
        logging.info("Starting Cloud System...")
        system = CloudSystem("localhost", "/status/cloud_system", "Cloud_System")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutting down gracefully...")
            
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        if 'system' in locals():
            system.cleanup()
        logging.info("Cloud System stopped")