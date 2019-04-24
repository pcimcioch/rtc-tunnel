import asyncio

from socket_connection import SocketConnection


class SocketClient:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._connection = None
        self._connected = asyncio.Event()

    async def connect_async(self):
        self._connected.clear()

        reader, writer = await asyncio.open_connection(
            host=self._host,
            port=self._port)
        print('Connected to %s:%s' % (self._host, self._port))
        self._connection = SocketConnection(reader, writer)

        self._connected.set()

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    async def receive_async(self):
        await self._connected.wait()
        return await self._connection.receive_async()

    async def send_async(self, data):
        await self._connected.wait()
        self._connection.send(data)