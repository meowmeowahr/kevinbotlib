import time

from kevinbotlib.hardware.interfaces.serial import RawSerialInterface

# ! remember to change these settings for your testing environment
gadget = RawSerialInterface("/dev/ttyUSB0", 9600)
# gadget.open() # * not needed if a port is provided above ^

while True:
    gadget.write(b"ping\n")
    print("Sent ping, waiting for pong...")

    while True:
        line = gadget.readline().decode("utf-8").rstrip()
        if line == "pong":
            print("Got pong")
            break

    time.sleep(1)
