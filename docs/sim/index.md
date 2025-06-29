# Simulation Framework

![sim-framework-marketing-image.gif](../media/sim-framework-marketing-image.gif)

The _KevinbotLib Simulation Framework_ allows for the testing of robot code before deployment.

## Architecture

![simulator-diagram-light.svg](../media/simulator-diagram-light.svg#only-light)
![simulator-diagram-dark.svg](../media/simulator-diagram-dark.svg#only-dark)

## Built-in Simulator WindowViews

### Process Time

![procinfo.png](../media/windowview/procinfo.png){ width=180px }

Display robot process running time, and robot cycle time

### Telemetry

![telemetry.png](../media/windowview/telemetry.png){ width=560px }

Display logs in real-time

### Metrics

![metrics.png](../media/windowview/metrics.png){ width=360px }

Display Robot Metrics

### Robot State

![state.png](../media/windowview/state.png){ width=220px }

Set the current OpMode, Enable, Disable, or E-Stop the robot

## Additional Simulator WindowViews

### Serial Devices

![serial.png](../media/windowview/serial.png){ width=480px }

Display each used Serial Interface in a tab

View more info [here](../hardware/interfaces/serial#simulation)

### Vision Cameras

![camera.png](../media/windowview/camera.png){ width=480px }

Simulate vision cameras by using local cameras, or image uploads

View more info [here](../vision/simulation)

## Using the Simulator Within a Robot

[`BaseRobot.run()`](../reference/robot.md#kevinbotlib.robot.BaseRobot.run) will automatically detect the `--simulate` command line flag.

The simulator can be detected at runtime using the [`BaseRobot.IS_SIM`](../reference/robot.md#kevinbotlib.robot.BaseRobot.IS_SIM) attribute, or if [`BaseRobot.simulator`](../reference/robot/#kevinbotlib.robot.BaseRobot.simulator) is a [`SimulationFramework`](../reference/simulator/#kevinbotlib.simulator.SimulationFramework) class.

### Examples

Any robot that correctly extends [`BaseRobot`](../reference/robot.md#kevinbotlib.robot.BaseRobot) is capable of running the simulator by using the `--simulate` command-line flag.

```python title="examples/robot/robot.py" linenums="1"
--8<-- "examples/robot/robot.py"
```

Run

```bash
python robot.py --simulate
```

## See Also

[Simulation Framework Reference](../reference/simulator.md)
