# The Command Scheduler

## Architecture Diagram

![scheduler-diagram-dark.svg](media/scheduler-diagram-dark.svg#only-dark)
![scheduler-diagram-light.svg](media/scheduler-diagram-light.svg#only-light)

## Why use the command scheduler?

The command scheduler offers a unique way to run commands in a robot program. 
Commands can be run in parallel, sequentially, or in the main scheduler FIFO queue.
This allows for more flexibility when compared with traditional linear programming.
Commands may be scheduled using a trigger.

## Examples

### Basic Usage

```python title="examples/scheduler/basic_example.py" linenums="1"
--8<-- "examples/scheduler/basic_example.py"
```

### Parallel Commands

```python title="examples/scheduler/parallel.py" linenums="1"
--8<-- "examples/scheduler/parallel.py"
```

### Sequential Commands

```python title="examples/scheduler/sequential.py" linenums="1"
--8<-- "examples/scheduler/sequential.py"
```

### Conditionally Forked Commands

```python title="examples/scheduler/conditionally_forked.py" linenums="1"
--8<-- "examples/scheduler/conditionally_forked.py"
```

### Named Controller Command Trigger

```python title="examples/scheduler/joystick_trigger.py" linenums="1"
--8<-- "examples/scheduler/joystick_trigger.py"
```
