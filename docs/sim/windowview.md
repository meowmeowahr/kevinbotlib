# WindowView API

## What is the WindowView API

The WindowView API is a framework for developing custom simulator subwindows using PySide6.
The simulator windows run in a separate process as the robot code, requiring the use of I/O queues for handling live data between the robot code and the simulator.

!!! Info
    The WindowView API requires the usage of [PySide6](https://doc.qt.io/qtforpython-6/).
    PySide6 versions not installed as a dependency of KevinbotLib, or other Python Qt bindings are not officially supported, and may not function properly.

## Creating and Registering a WindowView

```python title="examples/simulator/windowview_register.py" linenums="1"
--8<-- "examples/simulator/windowview_register.py"
```

!!! Tip
    Each WindowView must have a different registered Window ID (in this case, `test.mywindowview`). 
    It is recommended to use reverse domain name notation (e.g., `com.example.myproduct.mywindowview`).
    **Do not** use Window IDs starting with `kevinbotlib` or `com.meowmeowahr.kevinbotlib`

## Working with Payloads

```python title="examples/simulator/windowview_payload.py" linenums="1"
--8<-- "examples/simulator/windowview_payload.py"
```