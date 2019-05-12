# RTC Tunnel
This project uses WebRTC protocol to establish socket tunnel between two hosts

# Install
This project requires `aiortc`:
```
pip install aiortc
```
See details in <https://github.com/aiortc/aiortc>

# Run
Tu run server call:
```
python rtc-tunnel/server.py
```

Tu run client call:
```
python rtc-tunnel/client.py -p 3334 -d 22
```
Program will listen on port `3334` and forward all traffic from it to port `22` on seconond machine

# TODO
1. What does this application do exactly
1. How to run locally without signaling server
1. How to run locally with signaling server
1. How to run remotely with signaling server on heroku
1. Why no STOMP
1. Run options (arguments)
1. Implementation details