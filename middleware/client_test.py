#!/usr/bin/python
# coding:utf-8
import socket
import time
import uuid
import sys


def Check_Identity(data):
    if data == "VES":
        return True
    return False

if not sys.argv[1]:
    name = raw_input("Enter type(v for video,d for display):")
else:
    name = sys.argv[1]

broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  #
broad_sock.bind(('', 8089))
data = None
addr = None
while True:
    data, addr = broad_sock.recvfrom(4096)
    if Check_Identity(data) is True:
        break
broad_sock.close()
host = addr[0]
print 'Get broadcast message from host:', host
port = 8090 if name == "v" else 8092

ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # send socket
ss.connect((host, port))
while True:
    try:
        msg = str(uuid.uuid1())[:8]
        ss.send(msg)
        print 'Send message:', msg
    except:
        print 'Socket close.'
        break
    time.sleep(1)
