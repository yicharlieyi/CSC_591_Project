## **Overview**

The system utilizes two servo motors connected to designated GPIO pins on a Raspberry Pi. The servo motors control the opening and closing actions of the entry and exit gates. MQTT communication is used for real-time control commands from an external broker to the Raspberry Pi.

## **Hardware Requirements**

1. Raspberry Pi (any model with GPIO support)

2. Servo Motors (2 units: one for the entry gate, one for the exit gate)

3. Jumper Wires

4. Breadboard

5. Stable Power Supply

## **Software Requirements**

1. Python 3.x

2. RPi.GPIO: For GPIO control on the Raspberry Pi.

3. paho-mqtt: For MQTT messaging.

You can install the required Python libraries using pip:

**`pip install RPi.GPIO paho-mqtt`**

## **GPIO Pin Configuration**

1. Entry Gate Servo Motor: Connected to GPIO pin **18**.

2. Exit Gate Servo Motor: Connected to GPIO pin **13**.

## **MQTT Broker and Topics**

The code connects to an MQTT broker (by default, the IP is set to `44.204.193.8` on port `1883`). The following MQTT topics are used:

| Topic | Action |
| ----- | ----- |
| `/gate/entry/open` | Opens the entry gate |
| `/gate/entry/close` | Closes the entry gate |
| `/gate/exit/open` | Opens the exit gate |
| `/gate/exit/close` | Closes the exit gate |

*Note:* You can change the broker IP address as needed.

## **Code Details**

* **Servo Motor Functions:**

  - `open_gate(pwm)`: Activates the servo by changing the duty cycle to an angle corresponding to the "open" position (duty cycle of 5).

  - `close_gate(pwm)`: Changes the servo duty cycle to an angle corresponding to the "closed" position (duty cycle of 10).

* **MQTT Callbacks:**

  - `on_connect()`: Subscribes to all defined gate topics upon successful connection to the MQTT broker.

  - `on_message()`: Processes incoming messages and triggers the appropriate servo motor function:

    1. For the entry gate, topics `/gate/entry/open` and `/gate/entry/close` toggle the gate state.

    2. For the exit gate, topics `/gate/exit/open` and `/gate/exit/close` trigger the opening and closing actions.

* **Main Execution:**

  - The code sets the default state for the gates and establishes a connection with the MQTT broker.

  - The MQTT client then continuously listens for messages, controlling the servo motors accordingly.

  - A graceful cleanup of GPIO settings is performed upon termination.

## **Running the Code**

* **Connect the Hardware:**

  - Ensure that your servo motors are connected to the correct GPIO pins (18 for entry, 13 for exit).

  - Check all wiring and power connections.

* **Install Dependencies:**

Run the following command if you have not installed the required libraries:

**`pip install RPi.GPIO paho-mqtt`**

* **Execute the Script:**

Run the program using Python:

**`sudo python3 servo_motor.py`**

