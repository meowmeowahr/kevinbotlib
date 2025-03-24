# Hardware Interface Examples

## Serial Hardware Query Example

```python title="examples/hardware/serial_query.py" linenums="1"
--8<-- "examples/hardware/serial_query.py"
```

### Serial Raw Ping/Pong Example

!!! example
    ![Image title](../media/nano.png){ align=left }

    This example requires a serial device responding to pings to be connected.

    You can make one using the [Ping Pong Test Gadget](https://github.com/meowmeowahr/kevinbotlib-test-gadgets/tree/main/pingpong)

    The test gadget can be flashed to most PlatformIO compatible devices.

```python title="examples/hardware/serial_raw_ping_pong.py" linenums="1"
--8<-- "examples/hardware/serial_raw_ping_pong.py"
```

[^1]: Arduino Nano image modified from an original image by MakeMagazinDE, licensed under CC BY-SA 4.0 ([link](https://commons.wikimedia.org/wiki/File:Arduino_nano_isometr.jpg)).