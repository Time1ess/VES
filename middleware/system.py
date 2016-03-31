#!/usr/bin/python
# coding:UTF-8
__metaclass__ = type
import socket
import select

exit = False
# Set up broadcast socket
print 'Set up broadcast socket.'
broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
broad_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
broad_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
broad_host = '<broadcast>'
broad_port = 8089
broad_addr = (broad_host, broad_port)
broad_sock.bind(('', 0))

host = ''
video_port = 8090
display_port = 8091

# Prepare video terminal socket
print 'Prepare video terminal socket.'
video_terminal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_terminal.bind((host, video_port))
video_terminal.listen(1)

# Prepare display terminal socket
print 'Prepare display terminal socket.'
display_terminal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
display_terminal.bind((host, display_port))
display_terminal.listen(1)

waits = [video_terminal, display_terminal]
readys = {}
readys['display'] = None
readys['video'] = None

# Broadcast message until both terminals ready
print 'Start broadcasting.'
while True:
    if readys['display'] and readys['video']:
        break
    print 'Broadcast message.'
    broad_sock.sendto("VES", broad_addr)
    rs, ws, es = select.select(waits, [], [], 3)
    for r in rs:
        if r is video_terminal:
            client, addr = video_terminal.accept()
            print 'Video terminal get connection from', addr
            readys['video'] = client
        elif r is display_terminal:
            client, addr = display_terminal.accept()
            print 'Display terminal get connection from', addr
            readys['display'] = client
        else:
            print 'Unknown terminal.'

while True:
    if exit:
        print 'System shutdown.'
        break
    rs, ws, es = select.select(readys.values(), [], [], 3)
    for r in rs:
        try:
            msg = r.recv(4096)
            disconnected = not msg
        except:
            disconnected = True

        if r is readys['video']:
            if disconnected:
                print 'Video terminal disconnected.'
                exit = True
                del readys['video']
            else:
                print 'Get message from video   terminal:', msg
        elif r is readys['display']:
            if disconnected:
                print 'Display terminal disconnected.'
                exit = True
                del readys['display']
            else:
                print 'Get message from display terminal:', msg

# Memory recovery
print 'Begin memory recovery.'
