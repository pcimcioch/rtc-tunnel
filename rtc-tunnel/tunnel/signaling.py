import asyncio
import json
import sys
from json import JSONDecodeError

from aiortc import RTCSessionDescription, RTCIceCandidate
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp


class ConsoleSignaling:
    def __init__(self):
        self._read_pipe = sys.stdin
        self._read_transport = None
        self._reader = None
        self._write_pipe = sys.stdout

    async def connect(self):
        loop = asyncio.get_event_loop()
        self._reader = asyncio.StreamReader(loop=loop)
        self._read_transport, _ = await loop.connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(self._reader),
            self._read_pipe)

    def close(self):
        if self._reader is not None:
            self._read_transport.close()
            self._reader = None

    async def receive_async(self):
        print('-- Please enter a message from remote party --')
        while True:
            data = await self._reader.readline()
            print()
            try:
                return object_from_string(data.decode(self._read_pipe.encoding))
            except JSONDecodeError:
                print('Unable to parse signaling input as Json, ignoring')


    async def send_async(self, descr):
        print('-- Please send this message to the remote party --')
        self._write_pipe.write(object_to_string(descr) + '\n')
        print()


def object_to_string(obj):
    if isinstance(obj, RTCSessionDescription):
        message = {
            'sdp': obj.sdp,
            'type': obj.type
        }
    elif isinstance(obj, RTCIceCandidate):
        message = {
            'candidate': 'candidate:' + candidate_to_sdp(obj),
            'id': obj.sdpMid,
            'label': obj.sdpMLineIndex,
            'type': 'candidate',
        }
    else:
        raise ValueError('Can only send RTCSessionDescription or RTCIceCandidate')
    return json.dumps(message, sort_keys=True)


def object_from_string(message_str):
    message = json.loads(message_str)
    if message['type'] in ['answer', 'offer']:
        return RTCSessionDescription(**message)
    elif message['type'] == 'candidate':
        candidate = candidate_from_sdp(message['candidate'].split(':', 1)[1])
        candidate.sdpMid = message['id']
        candidate.sdpMLineIndex = message['label']
        return candidate