import random
import string
import time

import line_profiler

from kevinbotlib.comm.core.client import NetworkClientCore
from kevinbotlib.logger import Logger, LoggerConfiguration


def randomword(length):
    return "".join(random.choice(string.ascii_lowercase) for i in range(length))


DATA = randomword(10_000_000)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8888
NUM_OPERATIONS = 100  # Number of SET/GET operations for comparison


@line_profiler.profile
def run():
    client = NetworkClientCore(SERVER_HOST, SERVER_PORT)
    try:
        client.connect()

        # Phase 0: Static SET operations
        Logger().info(f"Starting {NUM_OPERATIONS} Static SET operations...")
        start_time_set = time.perf_counter()
        set_success_count = 0
        for _ in range(NUM_OPERATIONS):
            value = DATA
            if client.set("key_static", value):
                set_success_count += 1
        end_time_set = time.perf_counter()
        time_elapsed_set = end_time_set - start_time_set
        Logger().info(f"Completed {NUM_OPERATIONS} Static SET operations in {time_elapsed_set:.4f} seconds.")
        Logger().info(f"  Static SET success rate: {set_success_count}/{NUM_OPERATIONS}")
        if set_success_count > 0:
            Logger().info(
                f"  Average Static SET time per operation: {time_elapsed_set / set_success_count * 1000:.4f} ms"
            )

        # Phase 1: SET operations
        Logger().info(f"Starting {NUM_OPERATIONS} SET operations...")
        start_time_set = time.perf_counter()
        set_success_count = 0
        for i in range(NUM_OPERATIONS):
            key = f"key_{i}"
            value = DATA
            if client.set(key, value):
                set_success_count += 1
        end_time_set = time.perf_counter()
        time_elapsed_set = end_time_set - start_time_set
        Logger().info(f"Completed {NUM_OPERATIONS} SET operations in {time_elapsed_set:.4f} seconds.")
        Logger().info(f"  SET success rate: {set_success_count}/{NUM_OPERATIONS}")
        if set_success_count > 0:
            Logger().info(f"  Average SET time per operation: {time_elapsed_set / set_success_count * 1000:.4f} ms")

        # Phase 2: GET operations (retrieving previously set keys)
        Logger().info(f"Starting {NUM_OPERATIONS} GET operations...")
        start_time_get = time.perf_counter()
        get_success_count = 0
        for i in range(NUM_OPERATIONS):
            key = f"key_{i}"
            retrieved_value = client.get(key)
            # In a real test, you'd verify retrieved_value against the original
            if retrieved_value is not None and not retrieved_value.startswith("ERROR"):
                get_success_count += 1
        end_time_get = time.perf_counter()
        time_elapsed_get = end_time_get - start_time_get
        Logger().info(f"Completed {NUM_OPERATIONS} GET operations in {time_elapsed_get:.4f} seconds.")
        Logger().info(f"  GET success rate: {get_success_count}/{NUM_OPERATIONS}")
        if get_success_count > 0:
            Logger().info(f"  Average GET time per operation: {time_elapsed_get / get_success_count * 1000:.4f} ms")

    except RuntimeError as e:
        Logger().error(f"Client operation failed: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    Logger().configure(LoggerConfiguration())
    run()
