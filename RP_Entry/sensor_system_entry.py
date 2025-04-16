import time
import logging
import threading
import argparse
from RPi import GPIO
from pirc522 import RFID as rfid
import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes 
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import DistanceSensor


# === DEFINITIONS === #
# Time in seconds
# Distance in meters
ENTER_DIST = 1
EXIT_DIST = 0.0762 # 1
TIMEOUT = 10
CAR_TIME = 0.25
M2FT = 3.28084 # Meters to Feet


# === RPI GPIO PINS === #

# Define SPI Chip Select (CS) pins
READER_1_CS = 7
READER_2_CS = 8

READER_1_IRQ = 23
READER_2_IRQ = 24

READER_1_RST = 17
READER_2_RST = 27

US_1_TRIG = 6
US_2_TRIG = 16

US_1_ECHO = 13
US_2_ECHO = 26


# === STATES === #
WAIT = 1
ENTER = 2
RFID  = 3
EXIT  = 4
EXIT_CLOSE = 5

states = {
    1: "WAIT",
    2: "ENTER",
    3: "RFID",
    4: "EXIT"
}

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
    "exit_ultr_sensor_req":     "sensors/get/exit_ultra_sensor",
    "exit_ultr_sensor_resp":    "sensors/reply/exit_ultra_sensor"
}

entry_topics_subscribe = [5, 9, 12]
exit_topics_subscribe = [7, 11,13]


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Timestamp, log level, message
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]  # Output to console
)

class SensorSystem:
    def __init__(self, gate_type, broker_ip, status_topic, client_id, default_topic="/", default_qos=2):

        self.gate_type = gate_type
        self.broker_ip = broker_ip
        self.status_topic = status_topic
        self.default_topic = default_topic
        self.default_qos = default_qos
        self.client_id = client_id

        self.current_state = WAIT
        self.timer = None
        self.time_below_dist = None
        self.reset = threading.Event()
        self.response = None
        self.response_event = threading.Event()
        self.validate_response = None
        self.validate_response_event = threading.Event()
        self.distance = None
        self.distance_event = threading.Event()

        self.factory = PiGPIOFactory()
        if gate_type == "entry":
            self.rfid_reader = rfid(bus=0, device=1, pin_rst=READER_1_RST, pin_ce=READER_1_CS, pin_irq=READER_1_IRQ, pin_mode=GPIO.BCM, antenna_gain=7)
            self.exit_ultra_sensor = DistanceSensor(echo=US_1_ECHO, trigger=US_1_TRIG, max_distance=1, pin_factory=self.factory)
            self.exit_exit_ultra_sensor = DistanceSensor(echo=US_2_ECHO, trigger=US_2_TRIG, max_distance=1, pin_factory=self.factory)
        elif gate_type == "exit":
            self.rfid_reader = rfid(bus=0, device=0, pin_rst=READER_2_RST, pin_ce=READER_2_CS, pin_irq=READER_2_IRQ, pin_mode=GPIO.BCM, antenna_gain=7)
            # self.exit_ultra_sensor = DistanceSensor(echo=US_2_ECHO, trigger=US_2_TRIG, max_distance=1, pin_factory=self.factory)
            #self.enter_ultra_sensor = DistanceSensor(echo=US_1_ECHO, trigger=US_1_TRIG, max_distance=2, pin_factory=self.factory)

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


    def on_connect(self, client, userdata, flags, reason_code, properties):
        """CONNACK server response"""
        print(f"Connection: {reason_code}")
        client.publish(self.status_topic, "online", qos=self.default_qos, retain=True)

        for topic in topics.values():
            client.subscribe(topic, qos=self.default_qos)


    def on_message(self, client, userdata, msg):
        """Publish Callback"""
        payload = msg.payload.decode()  # Decode the message payload
        topic = msg.topic

        if topic == topics["exit_ultr_sensor_req"]:
            distance = self.exit_exit_ultra_sensor.distance
            self.publish(str(distance), topics["exit_ultr_sensor_resp"])

        elif topic == topics["exit_ultr_sensor_resp"]:
            self.distance = float(payload)
            self.distance_event.set()

        elif self.gate_type == "entry" and topic == topics['validate_able_enter_resp']:
            self.response = payload
            self.response_event.set()

        elif self.gate_type == "entry" and topic == topics['validate_entry_resp']:
            self.validate_response = payload
            self.validate_response_event.set()

        elif self.gate_type == "exit" and topic == topics['validate_able_exit_resp']:
            self.response = payload
            self.response_event.set()

        elif self.gate_type == "exit" and topic == topics['validate_exit_resp']:
            self.validate_response = payload
            self.validate_response_event.set()
        


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

            self.rfid_reader.cleanup()
            GPIO.cleanup()
        except:
            pass

    
    def publish(self, value, topic=None, retain=False):
        if topic is None:
            topic = self.default_topic
        self.client.publish(topic, value, qos=self.default_qos, retain=retain)


    def __del__(self):
        """Auto stop"""
        self.cleanup()


    def interrupt_action(self, reset_state):
        logging.warning(f"Timer expired, resetting to {states[reset_state]}")
        self.current_state = reset_state
        self.reset.set()
        self.time_below_dist = None
        self.close_gate()

    def set_timer(self, interval, reset_state):
        self.reset.clear()
        if self.timer is not None:
            self.timer.cancel()
        
        self.timer = threading.Timer(interval, self.interrupt_action, [reset_state])
        self.timer.start()


    def stop_timer(self):
        if self.timer is not None:
            self.timer.cancel()
        self.reset.clear()

    def send_valid_passage(self, uid):
        """Sends message to cloud telling it vehicle entered successfully"""
        if self.gate_type == "entry":
            topic = topics['validate_entry_req']
        elif self.gate_type == "exit":
            topic = topics['validate_exit_req']

        self.publish(uid, topic)


    def validate_able_to_scan(self, uid):
        """Requests from cloud server if vehicle is allowed to enter"""
        if self.gate_type == "entry":
            topic = topics['validate_able_enter_req']
        elif self.gate_type == "exit":
            topic = topics['validate_able_exit_req']

        self.publish(uid, topic)

        self.response_event.clear()

        # if not self.response_event.wait(TIMEOUT)
        while not self.reset.is_set() and not self.response_event.is_set():
            time.sleep(0.1)
        time.sleep(0.1)

        if self.response_event.is_set() and self.response == "true":
            self.response = None
            self.response_event.clear()
            return True
        
        self.response = None
        self.response_event.clear()

        return False
    
    def get_exit_ultra_distance(self):
        self.publish("get", topics["exit_ultr_sensor_req"])
        while not self.reset.is_set() and not self.response_event.is_set():
            time.sleep(0.01)
        time.sleep(0.01)
        
        if self.distance_event.is_set() and self.distance:
            self.response = None
            self.response_event.clear()
            return self.distance
        
        self.response = None
        self.response_event.clear()

        return 0
    
    def close_gate(self):
        """Tells gate to close"""
        if self.gate_type == "entry":
            topic = topics['entry_gate_close']
        elif self.gate_type == "exit":
            topic = topics['exit_gate_close']

        self.publish("close", topic)

    def open_gate(self):
        """Tells gate to open"""
        if self.gate_type == "entry":
            topic = topics['entry_gate_open']
        elif self.gate_type == "exit":
            topic = topics['exit_gate_open']

        self.publish("close", topic)

    # States:

    # Entry:
    #  - Wait for car

    # Enter State:
    #  - Enter when sense car with US 
    #  - Verifies car came in correct way
    #  - Exit when valid rfid exit_sensed
    #  - Reset: Timeout
    #  - Sends: Nothing

    # RFID State
    #  - Enter when rfid sensed
    #  - checks if valid / able to enter
    #  - Exit: valid rfid
    #  - Reset: Timeout
    #  - Sends: UID, timestamp

    # EXIT State
    #  - Enter if RFID Valid
    #  - Checks car actually entered
    #  - Exit: Car enters lot
    #  - Reset: Timeout
    #  - Sends: Nothing

    # EXIT_CLOSE State
    #  - Enter if car got detected passing gate
    #  - Checks car cleared gate
    #  - Exit: Car enters lot
    #  - Reset: Timeout
    #  - Sends: UID, timestamp, and that car entered

    def run(self):
        while True:

            if self.current_state == WAIT: # Wait for car
                self.stop_timer()
                self.current_state = ENTER
                # distance = self.enter_ultra_sensor.distance

                # if distance < EXIT_DIST: # validate car there for more than 0.5 seconds

                #     if self.time_below_dist is None:
                #         # Record the time when the distance first goes below EXIT_DIST
                #         self.time_below_dist = time.time()
                    
                #     # Check if the distance has stayed below EXIT_DIST for n seconds
                #     if time.time() - self.time_below_dist >= CAR_TIME:
                #         self.current_state = ENTER
                #         self.set_timer(TIMEOUT, WAIT)
                #         self.time_below_dist = None
                #         logging.info("Vehicle Detected at gate")
                # else:
                #     # If the distance is no longer below EXIT_DIST, reset the timer
                #     self.time_below_dist = None


            elif self.current_state == ENTER: # Check rfid valid
                uid = self.rfid_reader.read_id(True)
                if uid is not None:
                    logging.info(f"RFID UID {uid} sensed")
                    if self.validate_able_to_scan(uid):
                        self.current_state = EXIT
                        self.open_gate()
                        self.set_timer(TIMEOUT, WAIT)
                        self.time_below_dist = None
                        logging.info(f"Vehicle {uid} allowed to pass")
                    else:
                        logging.warning(f"Vehicle {uid} not allowed to pass")
                        self.current_state = WAIT

                # if self.enter_ultra_sensor.distance > ENTER_DIST: # means car left
                #     logging.info("Vehicle not detected at gate")
                #     self.current_state = WAIT


            elif self.current_state == EXIT: # Check car at least started passing gate
                if self.exit_ultra_sensor.distance < EXIT_DIST:

                    if self.time_below_dist is None:
                        self.time_below_dist = time.time()
                    
                    if time.time() - self.time_below_dist >= CAR_TIME: # valid for n seconds
                        # self.send_valid_entry(uid)
                        self.stop_timer()
                        self.current_state = EXIT_CLOSE
                        self.time_below_dist = None
                        logging.info("Vehicle successfully passed gate")
                else:
                    self.time_below_dist = None


            elif self.current_state == EXIT_CLOSE: # Checks no car there - can close gate
                if self.gate_type == "exit":
                    distance = self.get_exit_ultra_distance()
                else:
                    distance = self.exit_ultra_sensor.distance

                if distance > EXIT_DIST:

                    if self.time_below_dist is None:
                        self.time_below_dist = time.time()
                    
                    if time.time() - self.time_below_dist >= CAR_TIME: # valid for n seconds
                        self.send_valid_passage(uid)
                        self.close_gate()
                        self.current_state = WAIT
                        self.time_below_dist = None
                        logging.info("Vehicle successfully cleared gate")
                else:
                    self.time_below_dist = None

            time.sleep(0.1)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Process gate type argument.")
        parser.add_argument("gate_type", choices=["entry", "exit"], help="Specify gate type (entry or exit)", type=str)
        args = parser.parse_args()
        gate_type = args.gate_type

        system = SensorSystem(gate_type, "44.204.193.8", f"/status/sensor_system_{gate_type}", f"sensor_system_{gate_type}")
        system.run()
    except KeyboardInterrupt:
        logging.info("Exiting...")
