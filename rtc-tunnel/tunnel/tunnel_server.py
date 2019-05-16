import asyncio
import logging
import traceback

from aiortc import RTCSessionDescription, RTCPeerConnection, RTCDataChannel

from .util import now
from .tasks import Tasks
from .socket_client import SocketClient

class TunnelServer:
    def __init__(self, signal_server):
        self._signal_server = signal_server
        self._tasks = Tasks()
        self._running = asyncio.Event()

    async def run_async(self):
        while not self._running.is_set():
            logging.info('[INIT] Connecting with signaling server')
            await self._signal_server.connect_async()

            logging.info('[INIT] Awaiting offers from signaling server')
            while True:
                try:
                    obj, src = await self._signal_server.receive_async()
                except Exception:
                    break
                if isinstance(obj, RTCSessionDescription) and obj.type == 'offer':
                    await self._handle_new_client_async(obj, src)
                else:
                    logging.info('[WARNING] Unknown request from signaling server, ignoring')
            logging.info('[EXIT] Connection with signaling server broken')

    async def _handle_new_client_async(self, obj: RTCSessionDescription, src: str):
        logging.info('[CLIENT] Creating RTC Connection')
        peer_connection = RTCPeerConnection()
        await peer_connection.setRemoteDescription(obj)
        await peer_connection.setLocalDescription(await peer_connection.createAnswer())

        logging.info('[CLIENT] Sending local descriptor to signaling server')
        self._signal_server.send(peer_connection.localDescription, src)

        @peer_connection.on('datachannel')
        def on_datachannel(channel: RTCDataChannel):
            if channel.label == 'healthcheck':
                self._configure_healthcheck(channel, peer_connection)
                logging.info('[CLIENT] Established RTC connection')
                return

            name_parts = channel.label.split('-')
            if len(name_parts) == 3 and name_parts[0] == 'tunnel' and name_parts[2].isdigit():
                client_id = name_parts[1]
                port = int(name_parts[2])
                logging.info('[CLIENT %s] Connected to %s channel', client_id, channel.label)
                logging.info('[CLIENT %s] Connecting to 127.0.0.1:%s', client_id, port)
                client = SocketClient('127.0.0.1', port)
                self._tasks.start_task(client.connect_async())
                self._configure_channel(channel, client, client_id)
            else:
                logging.info('[CLIENT] Ignoring unknown datachannel %s', channel.label)

    def _configure_healthcheck(self, channel: RTCDataChannel, peer_connection: RTCPeerConnection):
        outer = {'last_healthcheck': now()}

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
            logging.info('[HEALTH CHECK] Datachannel timeout')
            await peer_connection.close()
        self._tasks.start_cancellable_task(healthcheck_loop_async())

    def _configure_channel(self, channel: RTCDataChannel, client: SocketClient, client_id: str):
        @channel.on('message')
        def on_message(message):
            client.send(message)

        @channel.on('close')
        def on_close():
            logging.info('[CLIENT %s] Datachannel %s closed', client_id, channel.label)
            client.close()

        async def receive_loop_async():
            await client.wait_until_connected_async()
            while True:
                try:
                    data = await client.receive_async()
                except Exception:
                    traceback.print_exc()
                    break
                if not data:
                    break
                channel.send(data)
            logging.info('[CLIENT %s] Socket connection closed', client_id)
            client.close()
            channel.close()

        self._tasks.start_task(receive_loop_async())
        logging.info('[CLIENT %s] Datachannel %s configured', client_id, channel.label)

    async def close_async(self):
        logging.info('[EXIT] Closing signalling server')
        self._running.set()
        if self._signal_server is not None:
            await self._signal_server.close_async()
        logging.info('[EXIT] Waiting for all tasks to finish')
        await self._tasks.close_async()
        logging.info('[EXIT] Closed tunneling server')
