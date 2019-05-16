import asyncio
import logging

from .socket_connection import SocketConnection


class SocketClient:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._connection = None
        self._connected = asyncio.Event()
        self._buffer = []

    async def connect_async(self):
        self._connected.clear()

        reader, writer = await asyncio.open_connection(host=self._host,port=self._port)
        logging.info('Connected to %s:%s', self._host, self._port)
        self._connection = SocketConnection(reader, writer)

        self._connected.set()

    def close(self):
        if self._connection is not None:
            self._connection.close()

    async def wait_until_connected_async(self):
        await self._connected.wait()

    async def receive_async(self):
        return await self._connection.receive_async()

    def send(self, data):
        # The problem is that we have to make channel configuration as soon as we get 'datachannel' event
        # But then we have to either:
        # 1. Open socket in blocking fashion - in the same coroutine - I'm not sure how to do this using asyncio (We have to remember that receive *MUST* be async!)
        # 2. Make 'send' async so we could add here 'await self._connected.wait()' - but then, as on_message can't be coroutine, put 'send' in separate asyncio task. We can't do this as we care about 'send' order
        # 3. Make 'send' blocking, but somehow prevent sending messages if connection is not yet established. That's the solution I've chosen. It's not perfect, but it works
        if self._connected.is_set():
            while len(self._buffer) > 0:
                self._connection.send(self._buffer.pop(0))
            self._connection.send(data)
        else:
            self._buffer.append(data)