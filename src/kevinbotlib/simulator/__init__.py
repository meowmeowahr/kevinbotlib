import multiprocessing

from kevinbotlib.simulator.simulator import SimulationFramework


def freeze_support() -> None:
    multiprocessing.freeze_support()


__all__ = ["SimulationFramework", "freeze_support"]
