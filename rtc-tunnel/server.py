#!/usr/bin/env python3

import argparse
import asyncio
import logging.handlers
import sys

from tunnel import TunnelServer
from tunnel.signaling import WebSignaling, ConsoleSignaling


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.handlers.TimedRotatingFileHandler('/tmp/rtc-server.log', when="midnight", backupCount=3),
        logging.StreamHandler(sys.stdout)
    ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RTC Tunneling server')
    parser.add_argument('--source-name', '-S', help='Source name', default='server')
    parser.add_argument('--use-web-signal', '-w', help='Enable web signal server instead of console', action='store_true')
    parser.add_argument('--signal-send-url', '-u', help='Signal server send url', default='http://user:password@192.168.0.114:8080')
    parser.add_argument('--signal-receive-url', '-r', help='Signal server receive url', default='ws://user:password@192.168.0.114:8080')
    args = parser.parse_args()

    if args.use_web_signal:
        signal_server = WebSignaling(args.source_name, args.signal_send_url, args.signal_receive_url)
    else:
        signal_server = ConsoleSignaling(args.source_name)
    server = TunnelServer(signal_server)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(server.run_async())
    except KeyboardInterrupt:  # CTRL+C pressed
        pass
    finally:
        loop.run_until_complete(server.close_async())
        loop.close()