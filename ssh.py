import asyncio

import sys
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import CopyAndPasteSignaling


async def consume_signaling(pc, signaling):
    while True:
        obj = await signaling.receive()

        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == 'offer':
                # send answer
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send(pc.localDescription)
        else:
            print('Exiting')
            break


async def run_answer(pc, signaling):
    await signaling.connect()

    @pc.on('datachannel')
    def on_datachannel(channel):
        print('created by remote party')

        @channel.on('message')
        def on_message(message):
            print(message)

            if isinstance(message, str) and message.startswith('ping'):
                channel.send('pong')

    await consume_signaling(pc, signaling)


async def run_offer(pc, signaling):
    await signaling.connect()

    channel = pc.createDataChannel('chat')
    print('created by local party')

    async def send_pings():
        while True:
            channel.send('ping')
            await asyncio.sleep(1)

    @channel.on('open')
    def on_open():
        asyncio.ensure_future(send_pings())

    @channel.on('message')
    def on_message(message):
        print(message)

    # send offer
    await pc.setLocalDescription(await pc.createOffer())
    await signaling.send(pc.localDescription)

    await consume_signaling(pc, signaling)


if __name__ == '__main__':
    signaling = CopyAndPasteSignaling()
    pc = RTCPeerConnection()

    role = sys.argv[1]
    if role == 'offer':
        coro = run_offer(pc, signaling)
    else:
        coro = run_answer(pc, signaling)

    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(pc.close())
        loop.run_until_complete(signaling.close())