import time
import logging
from tabulate import tabulate
from datetime import datetime
import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

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
    "validate_exit_resp":       "vehicle/validate_exit/response"
}

vehicles = {}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Timestamp, log level, message
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]  # Output to console
)

# STATUSES
OUT_LOT = 0
CHECKING_IN = 1
IN_LOT = 2
CHECKING_OUT = 3

# Definitions
LOT_CAPACITY = 4
WAIT_PERIOD = 30 # seconds

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

    def check_out(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.now()
        check_in_timestamp = self.check_ins[-1]

        self.check_outs.append(timestamp)

        session = {
            "system_session_id": self.system_session,
            "vehicle_session_id": self.vehicle_session,
            "check_in": check_in_timestamp,
            "check_out": timestamp,
            "duration": timestamp - check_in_timestamp
        }
        self.sessions.append(session)

        self.state = OUT_LOT

        return session

    def able_check_in(self):
        self.attempt_check_ins.append(datetime.now())

        if len(self.attempt_check_ins) >= 2 and (datetime.now() - self.attempt_check_ins[-2]).total_seconds() < WAIT_PERIOD:
            return False
        
        if self.state not in {OUT_LOT}:
            return False
        
        return True
        
    def able_check_out(self):
        self.attempt_check_outs.append(datetime.now())

        if len(self.attempt_check_outs) >= 2 and (datetime.now() - self.attempt_check_outs[-2]).total_seconds() < WAIT_PERIOD:
            return False
        
        if self.state not in {IN_LOT}:
            return False
        
        return True
    

class CloudSystem:
    def __init__(self, broker_ip, status_topic, client_id, default_topic="/", default_qos=2):

        self.broker_ip = broker_ip
        self.status_topic = status_topic
        self.default_topic = default_topic
        self.default_qos = default_qos
        self.client_id = client_id

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv5)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(status_topic, "offline", qos=2, retain=True)
        properties=Properties(PacketTypes.CONNECT)
        properties.SessionExpiryInterval = 2 * 60 # min x secs

        if  self.client.connect(broker_ip,
                port=1883,
                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                properties=properties,
                keepalive=60) != 0:
            print("MQTT Connection could not be established")
            raise TimeoutError("MQTT Connection could not be established")

        self.client.loop_start()

        self.system_session = 0
        self.current_occupancy = 0


    def on_connect(self, client, userdata, flags, reason_code, properties):
        """CONNACK server response"""
        print(f"Connection: {reason_code}")
        client.publish(self.status_topic, "online", qos=self.default_qos, retain=True)
        
        for topic in topics.values():
            client.subscribe(topic, qos=self.default_qos)


    def on_message(self, client, userdata, msg): # TODO: add logging and error checking
        """Publish Callback"""
        payload = msg.payload.decode()
        topic = msg.topic

        if topic == topics["validate_able_enter_req"]:
            uid = payload
            vehicle = vehicles.get(uid)

            if not vehicle:
                vehicle = Vehicle(uid)
                vehicles[uid] = vehicle

            if self.current_occupancy >= LOT_CAPACITY:
                logging.info(f"Vehicle {uid} validated able enter - parking lot full")
                self.publish("false", topics['validate_able_enter_resp'])
            elif vehicle.able_check_in():
                self.publish("true", topics['validate_able_enter_resp'])
                logging.info(f"Vehicle {uid} validated able enter")
            else:
                self.publish("false", topics['validate_able_enter_resp'])
                logging.info(f"Vehicle {uid} did not validate able enter")


        elif topic == topics["validate_able_exit_req"]:
            uid = payload
            vehicle = vehicles.get(uid)

            if not vehicle: # TODO: what do since how car get in lot?
                self.publish("false", topics['validate_able_exit_resp'])
                logging.info(f"Vehicle {uid} unknown - did not register at gate - not validate able exit")

            elif vehicle.able_check_out():
                self.publish("true", topics['validate_able_exit_resp'])
                logging.info(f"Vehicle {uid} validated able exit")

            else:
                self.publish("false", topics['validate_able_exit_resp'])
                logging.info(f"Vehicle {uid} did not validate able exit")


        elif topic == topics["validate_entry_req"]:
            uid = payload
            self.system_session += 1
            self.current_occupancy += 1
            vehicle = vehicles.get(uid)
            vehicle.check_in(self.system_session)
            self.publish("true", topics['validate_entry_resp'])
            logging.info(f"Vehicle {uid} validated entry")


        elif topic == topics["validate_exit_req"]:
            uid = payload
            self.current_occupancy -= 1
            vehicle = vehicles.get(uid)
            session = vehicle.check_out()
            self.publish("true", topics['validate_exit_resp'])

            logging.info(f"Vehicle {uid} exited lot. \n\nSession info:\n" + tabulate(list(session.items()), tablefmt="plain") + "\n\n") # headers=["Field", "Value"]

        else:
            logging.info(f"Topic: {topic} -- Message: {payload}")


    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Graceful disconnect"""
        pass


    def cleanup(self):
        """Stop client process and cleanup objects"""
        try:
            msg = self.client.publish(self.status_topic, "offline", qos=self.default_qos, retain=True)
            msg.wait_for_publish()
            self.client.disconnect()
            self.client.loop_stop()
            del self.client
        except:
            pass

    
    def publish(self, value, topic=None, retain=False):
        if topic is None:
            topic = self.default_topic
        self.client.publish(topic, value, qos=self.default_qos, retain=retain)


    def __del__(self):
        """Auto stop"""
        self.cleanup()


if __name__ == "__main__":
    try:
        system = CloudSystem("localhost", "/status/cloud_system", "Cloud_System")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Exiting...")