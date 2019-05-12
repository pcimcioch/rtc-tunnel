import argparse
import asyncio
# TODO 1. Test with rsync
# TODO 2. Add signalling server
# TODO 3. Test on raspberry startup
from tunnel import TunnelClient
from tunnel.signaling import ConsoleSignaling

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RTC Tunneling client')
    parser.add_argument('--destination-port', '-d', help='Destination port', default=22)
    parser.add_argument('--source-port', '-s', help='Source port', default=3334)
    parser.add_argument('--source-name', '-S', help='Source name', default='client')
    parser.add_argument('--destination-name', '-D', help='Destination name', default='server')
    args = parser.parse_args()

    signal_server = ConsoleSignaling(args.source_name)
    client = TunnelClient('', args.source_port, args.destination_port, signal_server, args.destination_name)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run_async())
    except KeyboardInterrupt:  # CTRL+C pressed
        pass
    finally:
        loop.run_until_complete(client.close_async())
        loop.close()