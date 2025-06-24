# Serial

The serial interface will connect to a local serial device.

The serial interface is capable of connection to devices with arbitrary baud-rates (may not be supported on some hardware), flow control, parity, and differing stop bits.

!!! Note
    RS-485 support has not been tested yet. Feel free to submit a GitHub issue on your findings.

## Examples

### Serial Hardware Query

```python title="examples/hardware/serial_query.py" linenums="1"
--8<-- "examples/hardware/serial_query.py"
```

### Serial Raw Ping/Pong

!!! example
    ![Microcontroller](../../media/nano.png){ align=left }

    This example requires a serial device responding to pings to be connected.

    You can make one using the [Ping Pong Test Gadget](https://github.com/meowmeowahr/kevinbotlib-test-gadgets/tree/main/pingpong)

    The test gadget can be flashed to most PlatformIO compatible devices.

```python title="examples/hardware/serial_raw_ping_pong.py" linenums="1"
--8<-- "examples/hardware/serial_raw_ping_pong.py"
```

[^1]: Arduino Nano image modified from an original image by MakeMagazinDE, licensed under CC BY-SA 4.0 ([link](https://commons.wikimedia.org/wiki/File:Arduino_nano_isometr.jpg)).