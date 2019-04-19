import asyncio

import sys
import socket
import time

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
    @channel.on('message')
    def on_message(message):
        print('< ' + message)

    async def send_pings():
        while True:
            channel.send('from proxy')
            print('> from proxy')
            await asyncio.sleep(3)

    asyncio.ensure_future(send_pings())


def start_listening(channel):
    @channel.on('message')
    def on_message(message):
        print('< ' + message)

    async def send_pings():
        while True:
            channel.send('from listen')
            print('> from listen')
            await asyncio.sleep(5)

    asyncio.ensure_future(send_pings())


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