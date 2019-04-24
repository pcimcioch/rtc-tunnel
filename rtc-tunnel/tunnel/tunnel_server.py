import asyncio
import traceback

from aiortc import RTCSessionDescription, RTCPeerConnection, RTCDataChannel
from aiortc.contrib.signaling import CopyAndPasteSignaling
from .socket_client import SocketClient

class TunnelServer:
    def __init__(self):
        self._signal_server = None

    async def run_async(self):
        print('[INIT] Connecting with signaling server')
        self._signal_server = CopyAndPasteSignaling()
        await self._signal_server.connect()

        print('[INIT] Awaiting offers from signaling server')
        while True:
            obj = await self._signal_server.receive()
            if isinstance(obj, RTCSessionDescription) and obj.type == 'offer':
                await self._handle_new_client_async(obj)
            else:
                print('[EXIT] Signalling server closed connection')
                break

    async def _handle_new_client_async(self, obj: RTCSessionDescription):
        print('[CLIENT] Creating PeerConnection')
        peer_connection = RTCPeerConnection()
        await peer_connection.setRemoteDescription(obj)
        await peer_connection.setLocalDescription(await peer_connection.createAnswer())
        # TODO what to do on peer_connection error or close

        print('[CLIENT] Sending local descriptor to signaling server')
        await self._signal_server.send(peer_connection.localDescription)
        print('[CLIENT] Established RTC connection')

        @peer_connection.on('datachannel')
        def on_datachannel(channel: RTCDataChannel):
            name_parts = channel.label.split('-')
            if len(name_parts) == 3 and name_parts[0] == 'tunnel' and name_parts[2].isdigit():
                client_id = name_parts[1]
                port = int(name_parts[2])
                print('[CLIENT %s] Connected to %s channel' % (client_id, channel.label))
                print('[CLIENT %s] connecting to 127.0.0.1:%s' % (client_id, port))
                client = SocketClient('127.0.0.1', port)
                asyncio.ensure_future(client.connect_async())
                self._configure_channel(channel, client, client_id)
            else:
                print('[CLIENT] Ignoring unknown datachannel %s' % channel.label)

    def _configure_channel(self, channel: RTCDataChannel, client: SocketClient, client_id: str):
        @channel.on('message')
        def on_message(message):
            asyncio.ensure_future(client.send_async(message))

        @channel.on('close')
        def on_close():
            print('[CLIENT %s] Datachannel %s closed' % (client_id, channel.label))
            client.close()

        async def receive_loop_async():
            while True:
                try:
                    data = await client.receive_async()
                except Exception:
                    traceback.print_exc()
                    break
                if not data:
                    break
                channel.send(data)
            print('[CLIENT %s] Socket connection closed' % client_id)
            client.close()
            channel.close()

        asyncio.ensure_future(receive_loop_async())
        print('[CLIENT %s] Datachannel %s configured' % (client_id, channel.label))

    async def close_async(self):
        if self._signal_server is not None:
            await self._signal_server.close()
        # TODO remove peer connections?
