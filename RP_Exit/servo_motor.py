import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt

# --- GPIO Setup ---
ENTRY_MOTOR_PIN = 18
EXIT_MOTOR_PIN = 13

GPIO.setmode(GPIO.BCM)
GPIO.setup(ENTRY_MOTOR_PIN, GPIO.OUT)
GPIO.setup(EXIT_MOTOR_PIN, GPIO.OUT)

entry_pwm = GPIO.PWM(ENTRY_MOTOR_PIN, 50)
exit_pwm = GPIO.PWM(EXIT_MOTOR_PIN, 50)

entry_pwm.start(0)
exit_pwm.start(0)

# --- Servo Motor Functions ---
def open_gate(pwm):
    pwm.ChangeDutyCycle(5)  # Adjust for your servo
    time.sleep(1)
    pwm.ChangeDutyCycle(0)

def close_gate(pwm):
    pwm.ChangeDutyCycle(10)  # Adjust for your servo
    time.sleep(1)
    pwm.ChangeDutyCycle(0)

# --- MQTT Setup ---
BROKER = "44.204.193.8"
#BROKER = "54.174.26.220"
  # Replace with your broker
PORT = 1883

TOPICS = [
    ("/gate/entry/open", 0),
    ("/gate/entry/close", 0),
    ("/gate/exit/open", 0),
    ("/gate/exit/close", 0),
]

def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    client.subscribe(TOPICS)

def on_message(client, userdata, msg):
    topic = msg.topic.strip()
    print(f"Received message on topic: {topic}")

    if topic == "/gate/entry/open":
        print("Opening ENTRY gate")
        #open_gate(entry_pwm)
        close_gate(entry_pwm)

    elif topic == "/gate/entry/close":
        print("Closing ENTRY gate")
        #close_gate(entry_pwm)
        open_gate(entry_pwm)

    elif topic == "/gate/exit/open":
        print("Opening EXIT gate")
        open_gate(exit_pwm)

    elif topic == "/gate/exit/close":
        print("Closing EXIT gate")
        close_gate(exit_pwm)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print("Setting default state: gates closed")
    #close_gate(entry_pwm)
    open_gate(entry_pwm)
    close_gate(exit_pwm)

    print("Connecting to MQTT broker...")
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

except KeyboardInterrupt:
    print("Interrupted")

finally:
    print("Cleaning up GPIO")
    entry_pwm.stop()
    exit_pwm.stop()
    GPIO.cleanup()
