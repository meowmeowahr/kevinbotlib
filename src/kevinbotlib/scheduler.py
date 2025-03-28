from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self, TypedDict

from kevinbotlib.exceptions import (
    CommandSchedulerAlreadyExistsException,
    CommandSchedulerDoesNotExistException,
)


class Command(ABC):
    """Synchronous command interface that users will implement"""

    @abstractmethod
    def init(self) -> None:
        pass

    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def end(self) -> None:
        pass

    @abstractmethod
    def finished(self) -> bool:
        return False

    def then(self, next_command: "Command"):
        """Chain commands to run sequentially"""
        commands = self.startup_commands if isinstance(self, SequentialCommand) else [self]
        commands.append(next_command)
        return SequentialCommand(commands)

    def alongside(self, next_command: "Command"):
        """Chain commands to run sequentially"""
        commands = self.startup_commands if isinstance(self, ParallelCommand) else [self]
        commands.append(next_command)
        return ParallelCommand(commands)


class _SequencedCommand(TypedDict):
    command: Command
    has_init: bool


class SequentialCommand(Command):
    def __init__(self, commands: list[Command]) -> None:
        super().__init__()
        self.startup_commands = commands
        self.remaining_commands: list[_SequencedCommand] = [
            {"command": command, "has_init": False} for command in commands
        ]

    def init(self) -> None:
        self.remaining_commands: list[_SequencedCommand] = [
            {"command": command, "has_init": False} for command in self.startup_commands
        ]

    def execute(self) -> None:
        current_command = self.remaining_commands[0]
        if not current_command["has_init"]:
            current_command["command"].init()
            current_command["has_init"] = True

        current_command["command"].execute()

        if current_command["command"].finished():
            current_command["command"].end()
            self.remaining_commands.pop(0)

    def end(self) -> None:
        pass

    def finished(self) -> bool:
        return len(self.remaining_commands) == 0


class ParallelCommand(Command):
    def __init__(self, commands: list[Command]) -> None:
        super().__init__()
        self.startup_commands = commands
        self.remaining_commands: list[_SequencedCommand] = [
            {"command": command, "has_init": False} for command in commands
        ]

    def init(self) -> None:
        self.remaining_commands = [{"command": command, "has_init": False} for command in self.startup_commands]

    def execute(self) -> None:
        for command_info in self.remaining_commands[:]:
            command = command_info["command"]
            if not command_info["has_init"]:
                command.init()
                command_info["has_init"] = True

            command.execute()

            if command.finished():
                command.end()
                self.remaining_commands.remove(command_info)

    def end(self) -> None:
        for command_info in self.remaining_commands:
            command_info["command"].end()

    def finished(self) -> bool:
        return len(self.remaining_commands) == 0


@dataclass
class TriggerActions:
    on_true: Command | None = None
    on_false: Command | None = None
    while_true: Command | None = None
    while_false: Command | None = None


class Trigger:
    def __init__(self, trigger_func: Callable[[], bool], command_system: "CommandScheduler"):
        self.trigger_func = trigger_func
        self.command_system = command_system
        self.last_state: bool | None = None
        self.actions = TriggerActions()

    def check(self) -> tuple[bool, bool]:
        current_state = self.trigger_func()
        changed = current_state != self.last_state
        self.last_state = current_state
        return current_state, changed

    def on_true(self, command_instance: Command) -> "Trigger":
        self.actions.on_true = command_instance
        self.command_system.register_trigger(self)
        return self

    def on_false(self, command_instance: Command) -> "Trigger":
        self.actions.on_false = command_instance
        self.command_system.register_trigger(self)
        return self

    def while_true(self, command_instance: Command) -> "Trigger":
        self.actions.while_true = command_instance
        self.command_system.register_trigger(self)
        return self

    def while_false(self, command_instance: Command) -> "Trigger":
        self.actions.while_false = command_instance
        self.command_system.register_trigger(self)
        return self


class _ScheduledCommand(TypedDict):
    command: Command
    trigger: Trigger | None
    has_init: bool


class CommandScheduler:
    instance: Self | None = None

    def __init__(self) -> None:
        if CommandScheduler.instance:
            msg = "Another instance of CommandScheduler is running"
            raise CommandSchedulerAlreadyExistsException(msg)

        self._scheduled: list[_ScheduledCommand] = []
        self._triggers: list[Trigger] = []

    def get_instance(self):
        if CommandScheduler.instance:
            return CommandScheduler.instance
        raise CommandSchedulerDoesNotExistException

    def schedule(self, command: Command):
        self._schedule(command, None)

    def register_trigger(self, trigger: Trigger):
        self._triggers.append(trigger)

    def _schedule(self, command: Command, trigger: Trigger | None):
        self._scheduled.append({"command": command, "trigger": trigger, "has_init": False})

    def iterate(self):
        """
        Executes one iteration of the command scheduler, processing all scheduled commands
        and their triggers according to their current state and conditions.
        """
        # Get trigger states, determine if command should be run
        for trigger in self._triggers:
            current_state, state_changed = trigger.check()

            if current_state and state_changed and trigger.actions.on_true:
                self._schedule(trigger.actions.on_true, trigger)

            if not current_state and state_changed and trigger.actions.on_false:
                self._schedule(trigger.actions.on_false, trigger)

            if (
                current_state
                and trigger.actions.while_true
                and state_changed
                and not any(scheduled["command"] is trigger.actions.while_true for scheduled in self._scheduled)
            ):
                self._schedule(trigger.actions.while_true, trigger)

            if (
                not current_state
                and trigger.actions.while_false
                and state_changed
                and not any(scheduled["command"] is trigger.actions.while_false for scheduled in self._scheduled)
            ):
                self._schedule(trigger.actions.while_false, trigger)

        # Process all scheduled commands
        i = 0
        while i < len(self._scheduled):
            scheduled = self._scheduled[i]
            command = scheduled["command"]
            trigger = scheduled["trigger"]

            # Initialize command if not already initialized
            if not scheduled["has_init"]:
                command.init()
                scheduled["has_init"] = True

            # Check if trigger conditions are still satisfied for while_* commands
            if trigger:
                current_state, _ = trigger.check()
                is_while_command = (trigger.actions.while_true is command and not current_state) or (
                    trigger.actions.while_false is command and current_state
                )
                if is_while_command:
                    # End and remove the command if trigger conditions are no longer satisfied
                    command.end()
                    self._scheduled.pop(i)
                    continue

            # Execute command
            command.execute()

            # Check if command is finished
            if command.finished():
                command.end()
                self._scheduled.pop(i)
            else:
                i += 1
