import argparse
import asyncio
# TODO Add basic auth to signal server
# TODO Test on raspberry startup
# TODO Add readme guide
from tunnel import TunnelClient
from tunnel.signaling import WebSignaling
# from tunnel.signaling import ConsoleSignaling

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RTC Tunneling client')
    parser.add_argument('--destination-port', '-d', help='Destination port', default=22)
    parser.add_argument('--source-port', '-s', help='Source port', default=3334)
    parser.add_argument('--source-name', '-S', help='Source name', default='client')
    parser.add_argument('--destination-name', '-D', help='Destination name', default='server')
    parser.add_argument('--signal-send-url', '-u', help='Signal server send url', default='https://pc-signal-server.herokuapp.com')
    parser.add_argument('--signal-receive-url', '-r', help='Signal server receive url', default='wss://pc-signal-server.herokuapp.com')
    args = parser.parse_args()

    # signal_server = ConsoleSignaling(args.source_name)
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