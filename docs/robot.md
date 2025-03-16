# The Robot Class

!!! note
    The main robot class can only be used once within your project

!!! danger
    The safety features included within KevinbotLib are not guaranteed to always function.

    It is **always** recommended to add a physical emergency stop system to your robot.

The KevinbotLib main robot class is the starting point for your robotics project. It integrates many components of KevinbotLib together to make it easy to design your own robot.

## Features

The KevinbotLib Robot class sets up some components of KevinbotLib to make designing a robot easier. The components are listed below.

* Communication Server
* Communication Client
* Logging Configuration
* Periodic log file rotations
* Logging to HTML Server
* Control Console communication and management
* Robot operational mode management
* Safety features
* Signal shutdown support (POSIX only)

## Usage

* Extend the [BaseRobot](reference/index.md#kevinbotlib.robot.BaseRobot) class and add your own code.
* Call `YourRobotClassName().run()` to start the robot's execution
* All of the components listed above will be started up automatically 😀

!!! warning
    It is not recommended to override the `run` method, or any other private method marked with the `@final` decorator.

## Shutdown signals

!!! note
    The shutdown signals are only supported on POSIX OSes (like Linux or macOS). They are not supported on Windows due to the lack of user signals in the NT kernel.

### `SIGUSR1`

This will trigger a graceful system shutdown similar to `CTRL-C` on the console

This should leave the robot in a state where it's ready for a code restart

### `SIGUSR2`

This will trigger an **emergency shutdown** similar to hitting space on the Control Console

!!! example
    If the robot code's PID (process id) is 1234, you can run the following command to gracefully shut it down:
    
    ```bash
    kill -SIGUSR1 1234
    ```