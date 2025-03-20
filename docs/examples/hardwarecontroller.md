# Hardware Controller Examples

### Serial Raw Key/Value Protocol Example

!!! example
    ![Image title](../media/nano.png){ align=left }
    
    This example requires a serial device responding to commands to be connected.

    You can make one using the [Key/Value Test Gadget](https://github.com/meowmeowahr/kevinbotlib-test-gadgets/tree/main/keyvalue)

    The test gadget can be flashed to most PlatformIO compatible devices.

```python title="examples/hardware/serial_kv_controller.py" linenums="1" 
--8<-- "examples/hardware/serial_kv_controller.py"
```

[^1]: Arduino Nano image modified from an original image by MakeMagazinDE, licensed under CC BY-SA 4.0 ([link](https://commons.wikimedia.org/wiki/File:Arduino_nano_isometr.jpg)).