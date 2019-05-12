import traceback

from asyncio import StreamWriter, StreamReader


class SocketConnection:
    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self._reader = reader
        self._writer = writer

    def close(self):
        self._writer.close()

    def send(self, data):
        if not isinstance(data, (str, bytes)):
            raise ValueError('Cannot send unsupported data type: %s' % type(data))

        if data == '':
            user_data = b'\x00'
        elif isinstance(data, str):
            user_data = data.encode('utf8')
        elif data == b'':
            user_data = b'\x00'
        else:
            user_data = data

        try:
            self._writer.write(user_data)
        except Exception:
            traceback.print_exc()

    async def receive_async(self):
        return await self._reader.read(4096)