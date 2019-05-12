import argparse
import asyncio

from tunnel import TunnelServer
from tunnel.signaling import WebSignaling
# from tunnel.signaling import ConsoleSignaling

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RTC Tunneling server')
    parser.add_argument('--source-name', '-S', help='Source name', default='server')
    parser.add_argument('--signal-send-url', '-u', help='Signal server send url', default='https://pc-signal-server.herokuapp.com')
    parser.add_argument('--signal-receive-url', '-r', help='Signal server receive url', default='wss://pc-signal-server.herokuapp.com')
    args = parser.parse_args()

    # signal_server = ConsoleSignaling(args.source_name)
    signal_server = WebSignaling(args.source_name, args.signal_send_url, args.signal_receive_url)
    server = TunnelServer(signal_server)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(server.run_async())
    except KeyboardInterrupt:  # CTRL+C pressed
        pass
    finally:
        loop.run_until_complete(server.close_async())
        loop.close()