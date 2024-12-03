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

### Robot Estimated Timestamp Retrieval

=== "Serial"

    !!! note
        Serial mode does not support timestamps.

=== "MQTT"

    ```python title="examples/core/timestamp.py" linenums="1" 
    --8<-- "examples/core/timestamp.py"
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
