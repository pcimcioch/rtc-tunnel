import argparse
import asyncio
# TODO Test on raspberry startup as service
import logging.handlers
import sys

from tunnel import TunnelClient
from tunnel.signaling import WebSignaling, ConsoleSignaling


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.handlers.TimedRotatingFileHandler('/tmp/rtc-client.log', when="midnight", backupCount=3),
        logging.StreamHandler(sys.stdout)
    ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RTC Tunneling client')
    parser.add_argument('--destination-port', '-d', help='Destination port', default=22)
    parser.add_argument('--source-port', '-s', help='Source port', default=3334)
    parser.add_argument('--source-name', '-S', help='Source name', default='client')
    parser.add_argument('--destination-name', '-D', help='Destination name', default='server')
    parser.add_argument('--use-web-signal', '-w', help='Enable web signal server instead of console', action='store_true')
    parser.add_argument('--signal-send-url', '-u', help='Signal server send url', default='http://user:password@192.168.0.114:8080')
    parser.add_argument('--signal-receive-url', '-r', help='Signal server receive url', default='ws://user:password@192.168.0.114:8080')
    args = parser.parse_args()

    if args.use_web_signal:
        signal_server = WebSignaling(args.source_name, args.signal_send_url, args.signal_receive_url)
    else:
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