# Examples

All examples include two variants for serial, and MQTT.
Source code can be found [here](https://github.com/meowmeowahr/kevinbotlib/tree/main/examples)

For more information, see [Serial vs. MQTT](architecture.md#serial-vs-mqtt)

## Core

### Robot Connection

=== "Serial"

    ```python title="examples/core/connecting_serial.py" linenums="1" 
    --8<-- "examples/core/connecting_serial.py"
    ```

=== "MQTT"

    ```python title="examples/core/connecting.py" linenums="1" 
    --8<-- "examples/core/connecting.py"
    ```

### Robot Enabling and Disabling

=== "Serial"

    ```python title="examples/core/enable_serial.py" linenums="1" 
    --8<-- "examples/core/enable_serial.py"
    ```

=== "MQTT"

    ```python title="examples/core/enable.py" linenums="1" 
    --8<-- "examples/core/enable.py"
    ```

### Robot Emergency Stop

=== "Serial"

    ```python title="examples/core/estop_serial.py" linenums="1" 
    --8<-- "examples/core/estop_serial.py"
    ```

=== "MQTT"

    ```python title="examples/core/estop.py" linenums="1" 
    --8<-- "examples/core/estop.py"
    ```

### Robot State Retrieval

=== "Serial"

    ```python title="examples/core/state_serial.py" linenums="1" 
    --8<-- "examples/core/state_serial.py"
    ```

=== "MQTT"

    ```python title="examples/core/state.py" linenums="1" 
    --8<-- "examples/core/state.py"
    ```

### Robot Timestamp Retrieval <code class="doc-symbol doc-symbol-heading doc-symbol-mqtt">MQTT Only</code>

=== "MQTT"

    ```python title="examples/core/timestamp.py" linenums="1" 
    --8<-- "examples/core/timestamp.py"
    ```

### Robot Uptime Retrieval

=== "Serial"

    ```python title="examples/core/uptimes_serial.py" linenums="1" 
    --8<-- "examples/core/uptimes_serial.py"
    ```

=== "MQTT"

    ```python title="examples/core/uptimes.py" linenums="1" 
    --8<-- "examples/core/uptimes.py"
    ```

## Battery

### Robot Battery Readings

=== "Serial"

    ```python title="examples/battery/readings_serial.py" linenums="1" 
    --8<-- "examples/battery/readings_serial.py"
    ```

=== "MQTT"

    ```python title="examples/battery/readings.py" linenums="1" 
    --8<-- "examples/battery/readings.py"
    ```

## Environment

### BME280

=== "Serial"

    ```python title="examples/environment/bme280_serial.py" linenums="1" 
    --8<-- "examples/environment/bme280_serial.py"
    ```

=== "MQTT"

    ```python title="examples/environment/bme280.py" linenums="1" 
    --8<-- "examples/environment/bme280.py"
    ```

### DS18B20

=== "Serial"

    ```python title="examples/environment/ds18b20_serial.py" linenums="1" 
    --8<-- "examples/environment/ds18b20_serial.py"
    ```

=== "MQTT"

    ```python title="examples/environment/ds18b20.py" linenums="1" 
    --8<-- "examples/environment/ds18b20.py"
    ```


## IMU

### Periodic Polling

=== "Serial"

    ```python title="examples/imu/periodic_serial.py" linenums="1" 
    --8<-- "examples/imu/periodic_serial.py"
    ```

=== "MQTT"

    ```python title="examples/imu/periodic.py" linenums="1" 
    --8<-- "examples/imu/periodic.py"
    ```

### Plotting with matplotlib

=== "Serial"

    [https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/imu/plot_serial.py](https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/imu/plot_serial.py)

=== "MQTT"

    [https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/imu/plot.py](https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/imu/plot.py)

## Servo

### Sweep demo

=== "Serial"

    [https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/servo/sweep_serial.py](https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/servo/sweep_serial.py)

=== "MQTT"

    [https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/servo/sweep.py](https://github.com/meowmeowahr/kevinbotlib/blob/main/examples/servo/sweep.py)

## Drive

### Status

=== "Serial"

    ```python title="examples/drive/status_serial.py" linenums="1" 
    --8<-- "examples/drive/status_serial.py"
    ```

=== "MQTT"

    ```python title="examples/drive/status.py" linenums="1" 
    --8<-- "examples/drive/status.py"
    ```

### Drive at Power

=== "Serial"

    ```python title="examples/drive/drive_serial.py" linenums="1" 
    --8<-- "examples/drive/drive_serial.py"
    ```

=== "MQTT"

    ```python title="examples/drive/drive.py" linenums="1" 
    --8<-- "examples/drive/drive.py"
    ```
