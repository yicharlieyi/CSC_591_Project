import paho.mqtt.client as mqtt
from datetime import datetime

# MQTT Broker Details
broker = "test.mosquitto.org"  # MQTT broker address
port = 1883
topic = "door/status"  # MQTT topic

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # Subscribe to the topic
    client.subscribe(topic)

# Callback when a message is received
def on_message(client, userdata, message):
    payload = message.payload.decode()  # Decode the message payload
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get current timestamp
    print(f"[{timestamp}] Door Status: {payload}")

# Set up MQTT client
client = mqtt.Client()

# Assign callback functions
client.on_connect = on_connect
client.on_message = on_message

# Connect to the broker
client.connect(broker, port, 60)

# Start the loop to listen for messages
print("Listening for door status updates...")
client.loop_forever()