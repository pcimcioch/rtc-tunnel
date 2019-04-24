import asyncio
import traceback

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel
from aiortc.contrib.signaling import CopyAndPasteSignaling
from asyncio import StreamWriter, StreamReader
from socket_connection import SocketConnection


class TunnelClient:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
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
        self._server = await asyncio.start_server(
            self._handle_new_client,
            host=self._host,
            port=self._port)
        print('[INIT] Socket server started')
        print('[STARTED] Tunneling client started')
        print()

        await self._signal_server.receive()
        print('[EXIT] Signalling server closed connection')

    def _handle_new_client(self, reader: StreamReader, writer: StreamWriter):
        print('[CLIENT] New client connected')
        connection = SocketConnection(reader, writer)

        channel = self._peer_connection.createDataChannel('ssh-proxy')
        print('[CLIENT] Datachannel ssh-proxy created')

        @channel.on('open')
        def on_open():
            self._configure_channel(channel, connection)

    def _configure_channel(self, channel: RTCDataChannel, connection: SocketConnection):
        @channel.on('message')
        def on_message(message):
            connection.send(message)

        @channel.on('close')
        def on_close():
            print('[CLIENT] Channel closed')
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
            print('[CLIENT] Socket connection closed')
            connection.close()
            channel.close()

        asyncio.ensure_future(receive_loop_async())
        print('[CLIENT] Datachannel ssh-proxy configured')

    async def close_async(self):
        if self._signal_server is not None:
            await self._signal_server.close()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._peer_connection is not None:
            await self._peer_connection.close()

if __name__ == '__main__':
    client = TunnelClient('', 3334)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run_async())
    except KeyboardInterrupt:  # CTRL+C pressed
        pass
    finally:
        loop.run_until_complete(client.close_async())
        loop.close()