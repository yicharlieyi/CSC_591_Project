## **Overview**

The **sensor\_system\_exit.py** script is designed to:

* Monitor vehicles approaching and passing through the exit gate.

* Validate RFID tags for vehicles attempting to leave.

* Communicate with the cloud by publishing and subscribing to MQTT topics.

* Control the exit gate by issuing open/close commands based on sensor data and validation results.

## **Features**

* **Multi-State Operation:**  
   The system operates in several states (WAIT, ENTER, RFID, EXIT, EXIT\_CLOSE) to ensure that vehicles are properly detected and authenticated before the gate is opened and then closed after exit.

* **RFID Validation:**  
   Uses the MFRC522 RFID reader to capture and validate vehicle IDs. Validation results are communicated via MQTT topics.

* **Ultrasonic Sensing:**  
   Detection using ultrasonic sensors to confirm that a vehicle is present and has actually passed through the gate.

* **MQTT Communication:**  
   Publishes and subscribes to multiple MQTT topics for tasks such as validation requests/responses and sensor reading requests. The system handles both entry and exit topics based on the gate mode.

* **Error Handling and Timeout:**  
   Includes timer-based state resets to handle unexpected or prolonged sensor readings, ensuring the system recovers gracefully from errors.

## **Hardware Requirements**

1. **Raspberry Pi** ( 4, or similar with GPIO support)

2. **RFID Reader:** MFRC522 (or compatible)

3. **Ultrasonic Sensors:** At least one sensor for exit detection (using trigger and echo pins)

4. **Jumper Wires and Breadboard**

5. **Stable Power Supply**

### **GPIO Pin Assignments**

The following pin assignments are used in the code:

| Component | Pin / Connection |
| ----- | ----- |
| RFID Reader 1 (Entry) | CS: 7, RST: 17, IRQ: 23 |
| RFID Reader 2 (Exit) | CS: 8, RST: 27, IRQ: 24 |
| Ultrasonic Sensor 1 | TRIG: 6, ECHO: 13 |
| Ultrasonic Sensor 2 | TRIG: 16, ECHO: 26 |

## **Software Requirements**

1. **Python 3.x**

2. **RPi.GPIO:** For general-purpose I/O control.

3. **pirc522:** For interfacing with RFID readers.

4. **paho-mqtt:** For MQTT communication.

5. **gpiozero:** For easier handling of ultrasonic sensors using the PiGPIOFactory.

Install the required libraries using pip:

**`pip install RPi.GPIO pirc522 paho-mqtt gpiozero`**

##     **MQTT Topics**

The module uses a set of MQTT topics to facilitate communication:

| Topic Name | Purpose |
| ----- | ----- |
| `/gate/exit/open` | Command to open the exit gate |
| `/gate/exit/close` | Command to close the exit gate |
| `vehicle/able_exit/request` | Request for exit validation |
| `vehicle/able_exit/response` | Response to exit validation (true/false) |
| `vehicle/validate_exit/request` | Request to validate vehicle exit via RFID |
| `vehicle/validate_exit/response` | Response for exit RFID validation |
| `sensors/get/exit_ultra_sensor` | Request to get the distance measurement from the sensor |
| `sensors/reply/exit_ultra_sensor` | Respond with the current distance value |

## **Usage**

### **Running the Script**

* **Set Up the Hardware:**

  - Ensure that the RFID reader and ultrasonic sensors are connected to the designated GPIO pins.

  - Verify stable power and proper wiring of all components.

* **Install Dependencies:**

  - Install the required Python packages as mentioned above.

* **Run the Script:**

  - Open a terminal on your Raspberry Pi.

Execute the script with the following command (for exit gate mode):

**`sudo python3 sensor_system_exit.py exit`**

- The system will initialize, connect to the MQTT broker (default IP: `44.204.193.8` on port 1883), and begin processing sensor inputs.  
