import asyncio
import json
import sys
import requests
import websockets
from json import JSONDecodeError

from aiortc import RTCSessionDescription, RTCIceCandidate
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp


class ConsoleSignaling:
    def __init__(self, source: str):
        self._source = source
        self._read_pipe = sys.stdin
        self._read_transport = None
        self._reader = None
        self._write_pipe = sys.stdout

    async def connect_async(self):
        loop = asyncio.get_event_loop()
        self._reader = asyncio.StreamReader(loop=loop)
        self._read_transport, _ = await loop.connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(self._reader),
            self._read_pipe)

    async def close_async(self):
        if self._reader is not None:
            self._read_transport.close()

    async def receive_async(self):
        print('-- Please enter a message from remote party to [%s] --' % self._source)
        while True:
            data = await self._reader.readline()
            try:
                message = data.decode(self._read_pipe.encoding)
                obj, source = object_from_string(message)
                print()
                return obj, source
            except JSONDecodeError:
                pass

    def send(self, descr, dest: str):
        print('-- Please send this message to the remote party named [%s] --' % dest)
        message = object_to_string(descr, self._source)
        self._write_pipe.write(message + '\n')
        print()


class WebSignaling:
    def __init__(self, source: str, send_url: str, receive_url: str):
        self._source = source
        self._send_url = send_url
        self._receive_url = receive_url
        self._client = None

    async def connect_async(self):
        self._client = await websockets.connect(self._receive_url + '/topic/message/' + self._source)

    async def close_async(self):
        if self._client is not None:
            await self._client.close()

    async def receive_async(self):
        message = await self._client.recv()
        return object_from_string(message)

    def send(self, descr, dest: str):
        message = object_to_string(descr, self._source)
        response = requests.post(self._send_url + '/message/' + dest, data=message)
        if response.status_code != 200:
            raise IOError('Unable to send signaling message')


def object_to_string(obj, source: str):
    if isinstance(obj, RTCSessionDescription):
        data = {
            'sdp': obj.sdp,
            'type': obj.type
        }
    elif isinstance(obj, RTCIceCandidate):
        data = {
            'candidate': 'candidate:' + candidate_to_sdp(obj),
            'id': obj.sdpMid,
            'label': obj.sdpMLineIndex,
            'type': 'candidate',
        }
    else:
        raise ValueError('Can only send RTCSessionDescription or RTCIceCandidate')
    message = {
        'source': source,
        'data': data
    }
    return json.dumps(message, sort_keys=True)


def object_from_string(message_str):
    obj = json.loads(message_str)
    data = obj['data']
    source = obj['source']

    if data['type'] in ['answer', 'offer']:
        return RTCSessionDescription(**data), source
    elif data['type'] == 'candidate':
        candidate = candidate_from_sdp(data['candidate'].split(':', 1)[1])
        candidate.sdpMid = data['id']
        candidate.sdpMLineIndex = data['label']
        return candidate, source