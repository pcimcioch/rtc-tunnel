import asyncio
import random
import string
import traceback

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel
from asyncio import StreamWriter, StreamReader

from .util import now
from .tasks import Tasks
from .socket_connection import SocketConnection


class TunnelClient:
    def __init__(self, host: str, port: int, destination_port: int, signal_server, destination: str):
        self._host = host
        self._port = port
        self._destination_port = destination_port
        self._signal_server = signal_server
        self._destination = destination
        self._running = asyncio.Event()
        self._tasks = Tasks()
        self._server = None
        self._peer_connection = None

    async def run_async(self):
        self._running.clear()

        print('[INIT] Creating RTC Connection')
        self._peer_connection = RTCPeerConnection()
        self._create_healthcheck_channel()
        await self._peer_connection.setLocalDescription(await self._peer_connection.createOffer())

        print('[INIT] Connecting with signaling server')
        await self._signal_server.connect_async()

        print('[INIT] Sending local descriptor to signaling server')
        self._signal_server.send(self._peer_connection.localDescription, self._destination)

        print('[INIT] Awaiting answer from signaling server')
        obj, src = await self._signal_server.receive_async()
        if not isinstance(obj, RTCSessionDescription) or obj.type != 'answer':
            print('[ERROR] Unexpected answer from signaling server')
            return
        await self._peer_connection.setRemoteDescription(obj)
        print('[INIT] Established RTC connection')

        await self._signal_server.close_async()
        print('[INIT] Closed signaling server')

        print('[INIT] Starting socket server on [%s:%s]' % (self._host, self._port))
        self._server = await asyncio.start_server(self._handle_new_client,host=self._host,port=self._port)
        print('[INIT] Socket server started')
        print('[STARTED] Tunneling client started')
        print()

        await self._running.wait()
        print('[EXIT] Tunneling client main loop closing')

    def _create_healthcheck_channel(self):
        channel = self._peer_connection.createDataChannel('healthcheck')

        @channel.on('open')
        def on_open():
            outer = {'last_healthcheck': now()}

            @channel.on('close')
            def on_close():
                print('[HEALTH CHECK] Datachannel closed')
                self._running.set()

            @channel.on('message')
            def on_message(message):
                outer['last_healthcheck'] = now()

            async def healthcheck_loop_async():
                while now() - outer['last_healthcheck'] < 7000:
                    try:
                        channel.send('ping')
                        await asyncio.sleep(3)
                    except Exception:
                        break
                print('[HEALTH CHECK] Datachannel timeout')
                self._running.set()
            self._tasks.start_cancellable_task(healthcheck_loop_async())

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

        self._tasks.start_task(receive_loop_async())
        print('[CLIENT %s] Datachannel %s configured' % (client_id, channel.label))

    async def close_async(self):
        self._running.set()
        print('[EXIT] Closing signalling server')
        if self._signal_server is not None:
            await self._signal_server.close_async()
        print('[EXIT] Closing socket server')
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        print('[EXIT] Closing RTC connection')
        if self._peer_connection is not None:
            await self._peer_connection.close()
        print('[EXIT] Waiting for all tasks to finish')
        await self._tasks.close_async()
        print('[EXIT] Closed tunneling client')