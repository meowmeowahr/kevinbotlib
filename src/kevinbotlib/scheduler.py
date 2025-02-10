import asyncio
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Self

from kevinbotlib.exceptions import CommandSchedulerAlreadyExistsException


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

    def then(self, next_command: 'Command') -> 'SequentialCommand':
        """Chain commands to run sequentially"""
        return SequentialCommand([self, next_command])

class WaitCommand(Command):
    """A command that waits for a specified duration without blocking the event loop"""
    def __init__(self, duration_seconds: float):
        self.duration = duration_seconds
        self.end_time: float | None = None
        self._finished = False

    def init(self) -> None:
        self.end_time = time.time() + self.duration

    def execute(self) -> None:
        if not self.end_time:
            return

        if time.time() >= self.end_time:
            self._finished = True

    def end(self) -> None:
        pass

    def finished(self) -> bool:
        return self._finished

class SequentialCommand(Command):
    """Executes commands in sequence, respecting WaitCommands"""
    def __init__(self, commands: Sequence[Command]):
        self.commands = list(commands)
        self.current_index = 0
        self._finished = False
        self.current_command_initialized = False

    def init(self) -> None:
        pass

    def execute(self) -> None:
        if self.current_index > len(self.commands) - 1:
            self._finished = True
            return

        current_command = self.commands[self.current_index]

        if not self.current_command_initialized:
            current_command.init()
            self.current_command_initialized = True

        current_command.execute()

        if current_command.finished():
            current_command.end()
            self.current_index += 1
            self.current_command_initialized = False

        self._finished = self.current_index >= len(self.commands)

    def end(self) -> None:
        pass

    def finished(self) -> bool:
        return self._finished

    def then(self, next_command: Command) -> 'SequentialCommand':
        """Add another command to the sequence"""
        self.commands.append(next_command)
        return self

class ParallelCommand(Command):
    """Executes multiple commands in parallel within the same event loop"""
    def __init__(self, commands: Sequence[Command]):
        self.commands = commands
        self._finished = False

    def init(self) -> None:
        for cmd in self.commands:
            cmd.init()

    def execute(self) -> None:
        for cmd in self.commands:
            if not cmd.finished():
                cmd.execute()
        self._finished = all(cmd.finished() for cmd in self.commands)

    def end(self) -> None:
        for cmd in self.commands:
            cmd.end()

    def finished(self) -> bool:
        return self._finished

class ThreadedParallelCommand(Command):
    """Executes multiple commands in parallel using separate threads"""
    def __init__(self, commands: Sequence[Command]):
        self.commands = commands
        self._finished = False
        self._threads: list[threading.Thread] = []
        self._command_states: dict[Command, dict] = {}
        self._lock = threading.Lock()

    def init(self) -> None:
        for cmd in self.commands:
            cmd.init()
            self._command_states[cmd] = {
                'finished': False,
                'error': None
            }

    def _run_command(self, cmd: Command):
        try:
            while not cmd.finished() and not self._finished:
                cmd.execute()

            with self._lock:
                self._command_states[cmd]['finished'] = True

        except Exception as e:
            with self._lock:
                self._command_states[cmd]['error'] = e

    def execute(self) -> None:
        if not self._threads:
            for cmd in self.commands:
                thread = threading.Thread(target=self._run_command, args=(cmd,))
                thread.daemon = True
                self._threads.append(thread)
                thread.start()

        with self._lock:
            all_finished = all(state['finished'] for state in self._command_states.values())
            any_errors = any(state['error'] for state in self._command_states.values())

            if all_finished or any_errors:
                self._finished = True
                for state in self._command_states.values():
                    if state['error']:
                        raise state['error']

    def end(self) -> None:
        self._finished = True
        for thread in self._threads:
            thread.join(timeout=1.0)
        for cmd in self.commands:
            cmd.end()

    def finished(self) -> bool:
        return self._finished


class AsyncCommandWrapper:
    """Internal wrapper to convert sync commands to async"""
    def __init__(self, command: Command):
        self.command = command

    async def init(self) -> None:
        self.command.init()

    async def execute(self) -> None:
        self.command.execute()

    async def end(self) -> None:
        self.command.end()

    def finished(self) -> bool:
        return self.command.finished()

@dataclass
class TriggerActions:
    on_true: Command | None = None
    on_false: Command | None = None
    while_true: Command | None = None
    while_false: Command | None = None

class Trigger:
    def __init__(self, trigger_func: Callable[[], bool], command_system: 'CommandScheduler'):
        self.trigger_func = trigger_func
        self.command_system = command_system
        self.last_state: bool | None = None
        self.actions = TriggerActions()

    def check(self) -> tuple[bool, bool]:
        current_state = self.trigger_func()
        changed = current_state != self.last_state
        self.last_state = current_state
        return current_state, changed

    def on_true(self, command_instance: Command) -> 'Trigger':
        self.actions.on_true = command_instance
        self.command_system._register_trigger(self)
        return self

    def on_false(self, command_instance: Command) -> 'Trigger':
        self.actions.on_false = command_instance
        self.command_system._register_trigger(self)
        return self

    def while_true(self, command_instance: Command) -> 'Trigger':
        self.actions.while_true = command_instance
        self.command_system._register_trigger(self)
        return self

    def while_false(self, command_instance: Command) -> 'Trigger':
        self.actions.while_false = command_instance
        self.command_system._register_trigger(self)
        return self

class CommandScheduler:
    instance: Self | None = None

    def __init__(self):
        if CommandScheduler.instance is not None:
            raise CommandSchedulerAlreadyExistsException(
                "CommandScheduler is a singleton, use `CommandScheduler.instance` to access it."
            )
        CommandScheduler.instance = self
        self.triggers: list[Trigger] = []
        self.enabled = True
        self.running_tasks: dict[str, dict] = {}
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)

    def schedule(self, command_instance: Command) -> None:
        """Schedule a one-time command execution"""
        trigger = Trigger(lambda: True, self)
        trigger.on_true(command_instance)

    def _register_trigger(self, trigger: Trigger) -> None:
        if trigger not in self.triggers:
            self.triggers.append(trigger)

    async def _run_command(self, command: Command, action_name: str) -> None:
        wrapped = AsyncCommandWrapper(command)
        await wrapped.init()
        await wrapped.execute()
        await wrapped.end()

    async def _run_while_command(self, command: Command, action_name: str, trigger_state: bool) -> None:
        wrapped = AsyncCommandWrapper(command)
        await wrapped.init()
        self.running_tasks[f"{id(command)}_{action_name}"] = {"command": command, "active": True}
        await wrapped.execute()
        await wrapped.end()
        del self.running_tasks[f"{id(command)}_{action_name}"]

    async def _iterate_once(self) -> bool:
        """Single iteration of the command processing loop"""
        if not self.enabled:
            return False

        for trigger in self.triggers:
            trigger_state, trigger_changed = trigger.check()

            # Handle one-time triggers
            if trigger_changed:
                if trigger_state and trigger.actions.on_true:
                    await self._run_command(trigger.actions.on_true, "on_true")
                elif not trigger_state and trigger.actions.on_false:
                    await self._run_command(trigger.actions.on_false, "on_false")

            # Handle continuous triggers
            task_key = f"{id(trigger)}_while_true"
            if trigger_state and trigger.actions.while_true:
                if task_key not in self.running_tasks:
                    self.running_tasks[task_key] = {
                        "command": trigger.actions.while_true,
                        "active": True
                    }
                    self._event_loop.create_task(
                        self._run_while_command(trigger.actions.while_true, "while_true", True)
                    )
            elif task_key in self.running_tasks:
                self.running_tasks[task_key]["active"] = False
                del self.running_tasks[task_key]

            task_key = f"{id(trigger)}_while_false"
            if not trigger_state and trigger.actions.while_false:
                if task_key not in self.running_tasks:
                    self.running_tasks[task_key] = {
                        "command": trigger.actions.while_false,
                        "active": True
                    }
                    self._event_loop.create_task(
                        self._run_while_command(trigger.actions.while_false, "while_false", False)
                    )
            elif task_key in self.running_tasks:
                self.running_tasks[task_key]["active"] = False
                del self.running_tasks[task_key]

        return True

    def iterate(self) -> bool:
        """Synchronous interface for running one iteration of the command system"""
        return self._event_loop.run_until_complete(self._iterate_once())

    def disable(self) -> None:
        """Disable the command scheduler"""
        self.enabled = False
        for task_info in self.running_tasks.values():
            task_info["active"] = False
        self.running_tasks.clear()

    def enable(self) -> None:
        """Enable the command scheduler"""
        self.enabled = True
