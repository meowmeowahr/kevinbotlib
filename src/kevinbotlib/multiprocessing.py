import multiprocessing
import os
import signal
import threading

from kevinbotlib.logger import Level as _Level
from kevinbotlib.logger import Logger as _Logger
from kevinbotlib.logger import LoggerWriteOpts as _LoggerWriteOpts


class SafeTelemeterizedProcess(multiprocessing.Process):
    # noinspection PyDefaultArgument
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None):  # noqa: B006
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self._log_queue = multiprocessing.Queue()

        def _log_catcher():
            while True:
                entry = self._log_queue.get()
                if entry:
                    _Logger().log(*entry)
                    os._exit(signal.SIGTERM)

        _log_catcher_thread = threading.Thread(
            target=_log_catcher, daemon=True, name=f"kevinbotlib.multiprocessing.exceptionlogger.{id(self)}"
        )
        _log_catcher_thread.start()

    def run(self):
        try:
            super().run()
        except BaseException as e:  # noqa: BLE001
            self._log_queue.put_nowait(
                (
                    _Level.CRITICAL,
                    f"An exception was raised in a Process: {self.pid} - Full tracebacks are not available in a process",
                    _LoggerWriteOpts(depth=1, exception=e),
                )
            )
