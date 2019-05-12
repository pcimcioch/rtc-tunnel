import argparse
import asyncio
# TODO 1. Test with rsync
# TODO 3. Test on raspberry startup
from tunnel import TunnelClient
from tunnel.signaling import WebSignaling

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RTC Tunneling client')
    parser.add_argument('--destination-port', '-d', help='Destination port', default=22)
    parser.add_argument('--source-port', '-s', help='Source port', default=3334)
    parser.add_argument('--source-name', '-S', help='Source name', default='client')
    parser.add_argument('--destination-name', '-D', help='Destination name', default='server')
    parser.add_argument('--signal-send-url', '-u', help='Signal server send url', default='http://192.168.0.114:8080')
    parser.add_argument('--signal-receive-url', '-r', help='Signal server receive url', default='ws://192.168.0.114:8080')
    args = parser.parse_args()

    signal_server = WebSignaling(args.source_name, args.signal_send_url, args.signal_receive_url)
    client = TunnelClient('', args.source_port, args.destination_port, signal_server, args.destination_name)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run_async())
    except KeyboardInterrupt:  # CTRL+C pressed
        pass
    finally:
        loop.run_until_complete(client.close_async())
        loop.close()