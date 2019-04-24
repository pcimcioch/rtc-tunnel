import asyncio
import random
import string
import traceback

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel
from aiortc.contrib.signaling import CopyAndPasteSignaling
from asyncio import StreamWriter, StreamReader
from .socket_connection import SocketConnection


class TunnelClient:
    def __init__(self, host: str, port: int, destination_port: int):
        self._host = host
        self._port = port
        self._destination_port = destination_port
        self._signal_server = None
        self._server = None
        self._peer_connection = None

    async def run_async(self):
        print('[INIT] Creating PeerConnection')
        self._peer_connection = RTCPeerConnection()
        self._peer_connection.createDataChannel('init')
        await self._peer_connection.setLocalDescription(await self._peer_connection.createOffer())
        # TODO what to do on _peer_connection error or close

        print('[INIT] Connecting with signaling server')
        self._signal_server = CopyAndPasteSignaling()
        await self._signal_server.connect()

        print('[INIT] Sending local descriptor to signaling server')
        await self._signal_server.send(self._peer_connection.localDescription)

        print('[INIT] Awaiting answer from signaling server')
        obj = await self._signal_server.receive()
        if not isinstance(obj, RTCSessionDescription) or obj.type != 'answer':
            print('[ERROR] Unexpected answer from signaling server')
            return
        await self._peer_connection.setRemoteDescription(obj)
        print('[INIT] Established RTC connection')

        print('[INIT] Starting socket server on [%s:%s]' % (self._host, self._port))
        self._server = await asyncio.start_server(self._handle_new_client,host=self._host,port=self._port)
        print('[INIT] Socket server started')
        print('[STARTED] Tunneling client started')
        print()

        await self._signal_server.receive()
        print('[EXIT] Signalling server closed connection')

    def _handle_new_client(self, reader: StreamReader, writer: StreamWriter):
        client_id = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
        print('[CLIENT %s] New client connected' % client_id)
        connection = SocketConnection(reader, writer)

        channel = self._peer_connection.createDataChannel('tunnel-%s-%s' % (client_id, self._destination_port))
        print('[CLIENT %s] Datachannel %s created' % (client_id, channel.label))

        @channel.on('open')
        def on_open():
            self._configure_channel(channel, connection, client_id)

    def _configure_channel(self, channel: RTCDataChannel, connection: SocketConnection, client_id: str):
        @channel.on('message')
        def on_message(message):
            connection.send(message)

        @channel.on('close')
        def on_close():
            print('[CLIENT %s] Datachannel %s closed' % (client_id, channel.label))
            connection.close()

        async def receive_loop_async():
            while True:
                try:
                    data = await connection.receive_async()
                except Exception:
                    traceback.print_exc()
                    break
                if not data:
                    break
                channel.send(data)
            print('[CLIENT %s] Socket connection closed' % client_id)
            connection.close()
            channel.close()

        asyncio.ensure_future(receive_loop_async())
        print('[CLIENT %s] Datachannel %s configured' % (client_id, channel.label))

    async def close_async(self):
        if self._signal_server is not None:
            await self._signal_server.close()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._peer_connection is not None:
            await self._peer_connection.close()