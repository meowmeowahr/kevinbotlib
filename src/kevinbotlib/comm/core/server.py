# python_comm_example/async_server.py

import asyncio
import sys

from line_profiler import profile

from kevinbotlib.logger import Level, Logger, LoggerConfiguration


class NetworkServer:
    def __init__(self, host: str, port: int):
        self.data_store = {}
        self._host = host
        self._port = port

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @profile
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Handles a single client connection asynchronously.
        """
        addr = writer.get_extra_info("peername")
        Logger().info(f"Accepted connection from {addr}")

        try:
            while True:
                # Read a line from the client
                raw_data = await reader.readline()
                if not raw_data:
                    break  # Client disconnected

                message = raw_data.decode("utf-8").strip()

                parts = message.split(" ", 2)

                command = parts[0].upper()
                key = parts[1] if len(parts) > 1 else None
                value = parts[2] if len(parts) > 2 else None  # noqa: PLR2004

                if command == "SET" and key and value is not None:
                    if " " in key:
                        response = "ERROR Key contains spaces\n"
                        Logger().warning(f"Invalid key from {addr}: {message}")
                    else:
                        self.data_store[key] = value
                        response = "OK\n"
                elif command == "GET" and key:
                    response = (self.data_store[key] + "\n") if key in self.data_store else "ERROR Key not found\n"
                elif command == "DEL" and key:
                    if key in self.data_store:
                        del self.data_store[key]
                    response = "OK\n"
                elif command == "PING":
                    response = "PONG\n"
                elif command == "RDY":
                    response = "OK\n"
                else:
                    response = "ERROR Invalid command or arguments\n"
                    Logger().warning(f"Invalid command from {addr}: {message}")

                writer.write(response.encode("utf-8"))
                await writer.drain()

        except ConnectionResetError:
            Logger().info(f"Client {addr} disconnected unexpectedly.")
            sys.exit()
        finally:
            Logger().info(f"Closing connection for {addr}")
            writer.close()
            await writer.wait_closed()
            sys.exit()

    @profile
    async def main(self):
        """
        Starts the asynchronous server.
        """
        server = await asyncio.start_server(self.handle_client, self._host, self._port, limit=2 ** 32 - 1)
        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        Logger().info(f"Serving on {addrs}")

        async with server:
            await server.serve_forever()

    def run(self):
        asyncio.run(self.main())


if __name__ == "__main__":
    Logger().configure(LoggerConfiguration(level=Level.TRACE))

    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 8888

    try:
        server = NetworkServer(SERVER_HOST, SERVER_PORT)
        server.run()
    except KeyboardInterrupt:
        Logger().info("Server stopped by user (Ctrl+C)")
