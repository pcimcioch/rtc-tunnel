# RTC Tunnel

This project uses WebRTC protocol to establish socket tunnel between two hosts.

It was created to cover following use case:
I wanted to SSH connect to Raspberry PI that was in different network that my local PC.
Both networks are behind a NAT, so it's not so easy to create direct connection without help of third, publicly visible server that would serve as reverse SSH tunnel.

I decided to write this simple python application that uses WebRTC to establish p2p connection between two hosts and allows to tunnel any socket connection (not only SSH on 22).

Note, that this is not production ready solution. It's more like a Proof of concept that such connection may be possible.

Also note, that it is not always possible to establish p2p connection in WebRTC protocol, but for most common cases it works ok. And it's possible to solve this problem if you have access to TURN server.

You will also need publicly available signalling server, although it's used only to exchange few text messages at the beginning of communication. It's load is nothing compared to reverse SSH tunnel


## Install

This project `python3` and few dependencies that can be added using
```
pip install -r requirements.txt
```
Note that it is using [aiortc](https://github.com/aiortc/aiortc) library, and you may have problems installing it on the Windows. 
At least I had quite a few problems and decided to stick with Windows 10 Ubuntu WSL, which works like a charm .


## Run locally without signaling server

By default, both client and server will use console as signaling server. 
That means you will be asked to copy and paste manually some json messages from client to server and back to make it running.

On server (ex. RaspberryPI):
```
python rtc-tunnel/server.py
```

On client (ex. PC):
```
python rtc-tunnel/client.py -s 3334 -d 22
```

On client (PC), port `3334` will be opened and will listen for new connections. Each connection will be redirected to port `22` on server (RaspberryPI).

Run on client (PC):
```
ssh -p 3334 pi@localhost
```


## Run locally with simple web signaling server

Project [rtc-signal-server](https://github.com/pcimcioch/rtc-signal-server) contains simple web signaling server that can be used to communicate between two hosts.

On host that is available from both client (PC) and server (RaspberryPI) run rtc-signal-server application.
(For testing purposes this can be PC if Raspberry and PC are in the same network)
```
gradlew bootRun
```

Let's say signal server is available at `192.168.0.114:8080`

On server (ex. RaspberryPI):
```
python rtc-tunnel/server.py -w -u http://user:password@192.168.0.114:8080 -r ws://user:password@192.168.0.114:8080
```

On client (ex. PC):
```
python rtc-tunnel/client.py -s 3334 -d 22 -w -u http://user:password@192.168.0.114:8080 -r ws://user:password@192.168.0.114:8080
```

On client (PC), port `3334` will be opened and will listen for new connections. Each connection will be redirected to port `22` on server (RaspberryPI).

Run on client (PC):
```
ssh -p 3334 pi@localhost
```


## Run with remote signaling server

As I don't have publicly available server, I used [Heroku](https://heroku.com) free account that allows me to run one small app 24/7 in their cloud for free. 
There are few cloud providers that would allow you to host app for free like that. I used Heroku because it's simple:
1. Create new application
1. Select repository with [rtc-signal-server](https://github.com/pcimcioch/rtc-signal-server) as code source. I advise to fork this repo, as it may change in the future!
1. Select `gradle` Buildpack
1. Set ConfigVar `JAVA_OPTS`=`-Dspring.security.user.password=mypassword`

Application will be automatically built and deployed.

Let's say signal server is available at `https://my-signal-server.herokuapp.com` and it's configured to use password `mypassword`

On server (ex. RaspberryPI):
```
python rtc-tunnel/server.py -w -u https://user:mypassword@my-signal-server.herokuapp.com -r wss://user:mypassword@my-signal-server.herokuapp.com
```

On client (ex. PC):
```
python rtc-tunnel/client.py -s 3334 -d 22 -w -u https://user:mypassword@my-signal-server.herokuapp.com -r wss://user:mypassword@my-signal-server.herokuapp.com
```

On client (PC), port `3334` will be opened and will listen for new connections. Each connection will be redirected to port `22` on server (RaspberryPI).

Run on client (PC):
```
ssh -p 3334 pi@localhost
```


## Run options

Client's options:

| Flag                     | Default                                 | Description                                                                                                           |
|--------------------------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| -d, --destination-port   | 22                                      | Port on server that client should be forwarded to                                                                     |
| -s, --source-port        | 3334                                    | Port that listens for connections on the client                                                                       |
| -S, --source-name        | client                                  | Name of this client. Useful when multiple clients are connecting to one signaling server. Must be unique in such case |
| -D, --destination-name   | server                                  | Name of server we are connecting to. Useful when multiple servers are connecting to single signaling server           |
| -w, --use-web-signal     | false                                   | Whether to use signaling using rtc-signal-server. If false, console will be used for signaling                        |
| -u, --signal-send-url    | http://user:password@192.168.0.114:8080 | Only used when -w is enabled. Http endpoint to send signal messages                                                   |
| -r, --signal-receive-url | ws://user:password@192.168.0.114:8080   | Only used when -w is enabled. WebSocket endpoint to receive messages from signal server                               |

Server's options:

| Flag                     | Default                                 | Description                                                                                                           |
|--------------------------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| -S, --source-name        | server                                  | Name of this server. Useful when multiple servers are connecting to one signaling server. Must be unique in such case |
| -w, --use-web-signal     | false                                   | Whether to use signaling using rtc-signal-server. If false, console will be used for signaling                        |
| -u, --signal-send-url    | http://user:password@192.168.0.114:8080 | Only used when -w is enabled. Http endpoint to send signal messages                                                   |
| -r, --signal-receive-url | ws://user:password@192.168.0.114:8080   | Only used when -w is enabled. WebSocket endpoint to receive messages from signal server                               |


## Implementation

TODO