import asyncio
import fnmatch

from kevinbotlib.logger import Level, Logger, LoggerConfiguration


class NetworkServer:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self.data_store = {}
        self.subscribers = {}  # pattern -> list of writers
        self.lock = asyncio.Lock()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        Logger().info(f"Accepted connection from {addr}")

        try:
            # Expect client to declare role first: ROLE SETGET or ROLE PUBSUB
            role_line = await reader.readline()
            if not role_line:
                writer.close()
                await writer.wait_closed()
                return
            role = role_line.decode().strip().upper()

            if role == "ROLE SETGET":
                await self.handle_setget(reader, writer, addr)
            elif role == "ROLE PUBSUB":
                await self.handle_pubsub(reader, writer, addr)
            else:
                writer.write(b"ERROR Unknown role\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            Logger().error(f"Error with client {addr}: {e}")
            writer.close()
            await writer.wait_closed()

    async def handle_setget(self, reader, writer, addr):
        while True:
            raw_data = await reader.readline()
            if not raw_data:
                break
            message = raw_data.decode().strip()
            if not message:
                continue

            parts = message.split(" ", 2)
            command = parts[0].upper()
            key = parts[1] if len(parts) > 1 else None
            value = parts[2] if len(parts) > 2 else None

            response = await self.process_setget(command, key, value)
            writer.write(response.encode())
            await writer.drain()

        Logger().info(f"Closing SETGET connection for {addr}")
        writer.close()
        await writer.wait_closed()

    async def handle_pubsub(self, reader, writer, addr):
        sub_patterns = []
        try:
            while True:
                raw_data = await reader.readline()
                if not raw_data:
                    break
                message = raw_data.decode().strip()
                if not message:
                    continue

                parts = message.split(" ", 2)
                command = parts[0].upper()
                key = parts[1] if len(parts) > 1 else None
                value = parts[2] if len(parts) > 2 else None

                if command == "SUB" and key:
                    await self.add_subscriber(writer, key)
                    sub_patterns.append(key)
                elif command == "PUB" and key and value is not None:
                    await self.broadcast(key, value)
                    writer.write(b"OK\n")
                    await writer.drain()
                elif command == "PING":
                    writer.write(b"PONG\n")
                    await writer.drain()
                elif command == "RDY":
                    writer.write(b"OK\n")
                    await writer.drain()
                elif command == "UNSUB" and key:
                    await self.remove_subscriber(writer, key)
                else:
                    writer.write(b"ERROR Invalid PUBSUB command\n")
                    await writer.drain()
        finally:
            # Cleanup subscriptions
            for pattern in sub_patterns:
                await self.remove_subscriber(writer, pattern)
            Logger().info(f"Closing PUBSUB connection for {addr}")
            writer.close()
            await writer.wait_closed()

    async def process_setget(self, command, key, value):
        async with self.lock:
            if command == "SET" and key and value is not None:
                self.data_store[key] = value
                return "OK\n"
            elif command == "GET" and key:
                return self.data_store.get(key, "ERROR Key not found") + "\n"
            elif command == "DEL" and key:
                self.data_store.pop(key, None)
                return "OK\n"
            elif command == "GKC":
                return f"{len(self.data_store)}\n"
            elif command == "GAK":
                return " ".join(self.data_store.keys()) + "\n"
            elif command == "KEY" and key:
                result = " ".join(fnmatch.filter(self.data_store.keys(), key))
                return result + ("\n" if result else "")
            elif command == "PING":
                return "PONG\n"
            elif command == "RDY":
                return "OK\n"
            elif command == "CLR":
                self.data_store.clear()
                return "OK\n"
            else:
                return "ERROR Invalid command\n"

    async def add_subscriber(self, writer, pattern):
        async with self.lock:
            if pattern not in self.subscribers:
                self.subscribers[pattern] = []
            self.subscribers[pattern].append(writer)
            Logger().info(f"Client subscribed to '{pattern}'")

    async def remove_subscriber(self, writer, pattern):
        async with self.lock:
            if pattern in self.subscribers:
                try:
                    self.subscribers[pattern].remove(writer)
                    Logger().info(f"Client unsubscribed from '{pattern}'")
                except ValueError:
                    pass
                if not self.subscribers[pattern]:
                    del self.subscribers[pattern]

    async def broadcast(self, key, value):
        async with self.lock:
            for pattern, writers in list(self.subscribers.items()):
                if fnmatch.fnmatch(key, pattern):
                    for w in writers[:]:
                        try:
                            w.write(f"PUB {key} {value}\n".encode())
                            await w.drain()
                        except Exception:
                            writers.remove(w)

    async def main(self):
        server = await asyncio.start_server(self.handle_client, self._host, self._port)
        Logger().info(f"Serving on {self._host}:{self._port}")
        async with server:
            await server.serve_forever()

    def run(self):
        asyncio.run(self.main())
