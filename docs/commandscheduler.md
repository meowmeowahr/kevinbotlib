# The Command Scheduler

## Architecture Diagram

![scheduler-diagram-dark.svg](media/scheduler-diagram-dark.svg#only-dark)
![scheduler-diagram-light.svg](media/scheduler-diagram-light.svg#only-light)

## Why use the command scheduler?

The command scheduler offers a unique way to run commands in a robot program. 
Commands can be run in parallel, sequentially, or in the main scheduler FIFO queue.
This allows for more flexibility when compared with traditional linear programming.
Commands may be scheduled using a trigger.
