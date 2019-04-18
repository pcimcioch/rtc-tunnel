import asyncio

import sys
import socket
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import CopyAndPasteSignaling


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


def start_proxy(channel):
    print('creating socket to port ', 22)
    sock = socket.socket()
    sock.connect(('127.0.0.1', 22))
    print('created!')

    # relay channel -> socket
    @channel.on('message')
    def on_message(message):
        print('sending to socket')
        sock.send(message)
        print('sent to socket')

    # relay socket -> channel
    async def socket_reader():
        while True:
            data = sock.recv(1024)
            if not data:
                print('breaking connection')
                break
            print('sending to channel')
            channel.send(data)
            print('sent to channel')
        sock.close()

    asyncio.ensure_future(socket_reader())


def start_listening(channel):
    print('listening on port ', 2222)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 2222))
    sock.listen(1)
    conn, addr = sock.accept()
    print('started!')

    # relay channel -> socket
    @channel.on('message')
    def on_message(message):
        print('sending to socket')
        conn.send(message)
        print('sent to socket')

    # relay socket -> channel
    async def socket_reader():
        while True:
            data = conn.recv(1024)
            if not data:
                print('breaking connection')
                break
            print('sending to channel')
            channel.send(data)
            print('sent to channel')
        conn.close()

    asyncio.ensure_future(socket_reader())


async def run_answer(connection, signal_server):
    await signal_server.connect()

    @connection.on('datachannel')
    def on_datachannel(channel):
        if channel.label == 'ssh-proxy':
            start_proxy(channel)

    await consume_signaling(connection, signal_server)


async def run_offer(connection, signal_server):
    await signal_server.connect()

    channel = connection.createDataChannel('ssh-proxy')
    print('created by local party')

    @channel.on('open')
    def on_open():
        start_listening(channel)

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