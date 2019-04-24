import asyncio
# TODO add readme
# TODO test with rsync
# TODO add signalling server
# TODO test on raspberry startup
from tunnel import TunnelClient

if __name__ == '__main__':
    client = TunnelClient('', 3334, 22)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run_async())
    except KeyboardInterrupt:  # CTRL+C pressed
        pass
    finally:
        loop.run_until_complete(client.close_async())
        loop.close()