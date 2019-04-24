import asyncio

import sys
import traceback

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import CopyAndPasteSignaling
from socket import AF_INET, socket, SOCK_STREAM


class TcpConsumer:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._reader = None
        self._writer = None
        self._connected = None

    async def connect(self):
        self._connected = asyncio.Event()
        self._reader, self._writer = await asyncio.open_connection(
            host=self._host,
            port=self._port)
        self._connected.set()
        print('Connected to port %s' % self._port)

    async def close(self):
        if self._writer is not None:
            self._writer.close()
            self._reader = None
            self._writer = None
            self._connected = None

    async def receive(self):
        await self._connected.wait()
        try:
            return await self._reader.read(1024)
        except Exception:
            traceback.print_exc()
            return

    async def send(self, data):
        if not isinstance(data, (str, bytes)):
            raise ValueError('Cannot send unsupported data type: %s' % type(data))

        if data == '':
            user_data = b'\x00'
        elif isinstance(data, str):
            user_data = data.encode('utf8')
        elif data == b'':
            user_data = b'\x00'
        else:
            user_data = data

        await self._connected.wait()
        try:
            self._writer.write(user_data)
        except Exception:
            traceback.print_exc()
            return


class TcpConsumer2:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._socket = None

    def connect(self):
        self._socket = socket(AF_INET, SOCK_STREAM)
        self._socket.connect((self._host, self._port))
        print('Connected to port %s' % self._port)

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def receive(self):
        try:
            return self._socket.recv(1024)
        except Exception:
            traceback.print_exc()
            return

    def send(self, data):
        if not isinstance(data, (str, bytes)):
            raise ValueError('Cannot send unsupported data type: %s' % type(data))

        if data == '':
            user_data = b'\x00'
        elif isinstance(data, str):
            user_data = data.encode('utf8')
        elif data == b'':
            user_data = b'\x00'
        else:
            user_data = data

        try:
            self._socket.send(user_data)
        except Exception:
            traceback.print_exc()
            return


class TcpProvider:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._reader = None
        self._writer = None
        self._server = None
        self._connected = None

    async def connect(self):
        self._connected = asyncio.Event()

        def client_connected(reader, writer):
            print('New client connected to port %s' % self._port)
            self._reader = reader
            self._writer = writer
            self._connected.set()

        self._server = await asyncio.start_server(
            client_connected,
            host=self._host,
            port=self._port)
        print('Listening for connections on port %s' % self._port)
        await self._connected.wait()

    async def close(self):
        if self._writer is not None:
            self._writer.close()
            self._reader = None
            self._writer = None
        if self._server is not None:
            self._server.close()
            self._server = None
        self._connected = None

    async def receive(self):
        try:
            return await self._reader.read(1024)
        except Exception:
            traceback.print_exc()
            return

    def send(self, data):
        if self._writer is None:
            print('Provider not sending - client not connected')
            return

        if not isinstance(data, (str, bytes)):
            raise ValueError('Cannot send unsupported data type: %s' % type(data))

        if data == '':
            user_data = b'\x00'
        elif isinstance(data, str):
            user_data = data.encode('utf8')
        elif data == b'':
            user_data = b'\x00'
        else:
            user_data = data

        try:
            self._writer.write(user_data)
        except Exception:
            traceback.print_exc()
            return


async def consume_signaling(connection, signal_server):
    while True:
        obj = await signal_server.receive()

        if isinstance(obj, RTCSessionDescription):
            await connection.setRemoteDescription(obj)

            if obj.type == 'offer':
                await connection.setLocalDescription(await connection.createAnswer())
                await signal_server.send(connection.localDescription)
        else:
            print('Exiting')
            break


def start_providing(channel, tcp):
    @channel.on('message')
    def on_message(message):
        asyncio.ensure_future(tcp.send(message))

    async def receive_data():
        while True:
            data = await tcp.receive()
            channel.send(data)

    asyncio.ensure_future(receive_data())


def start_consuming(channel, tcp):
    @channel.on('message')
    def on_message(message):
        tcp.send(message)

    async def receive_data():
        while True:
            data = await tcp.receive()
            channel.send(data)

    asyncio.ensure_future(receive_data())


async def run_answer(connection, signal_server):
    await signal_server.connect()

    @connection.on('datachannel')
    def on_datachannel(channel):
        if channel.label == 'ssh-proxy':
            tcp = TcpConsumer('127.0.0.1', 22)
            asyncio.ensure_future(tcp.connect())
            start_providing(channel, tcp)

    await consume_signaling(connection, signal_server)


async def run_offer(connection, signal_server):
    await signal_server.connect()
    tcp = TcpProvider('', 3334)
    await tcp.connect()

    channel = connection.createDataChannel('ssh-proxy')
    print('Channel created')

    @channel.on('open')
    def on_open():
        start_consuming(channel, tcp)

    # send offer
    await connection.setLocalDescription(await connection.createOffer())
    await signal_server.send(connection.localDescription)

    await consume_signaling(connection, signal_server)


if __name__ == '__main__':
    signal_server = CopyAndPasteSignaling()
    connection = RTCPeerConnection()

    role = sys.argv[1]
    if role == 'offer':
        coro = run_offer(connection, signal_server)
    else:
        coro = run_answer(connection, signal_server)

    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(connection.close())
        loop.run_until_complete(signal_server.close())