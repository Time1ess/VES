#!/usr/bin/python
# coding:utf-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-04 14:10
# Last modified: 2016-04-11 10:01
# Filename: client_test.py
# Description:
import socket
import time
import sys
import select
from random import randint


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

client = None
if name == "v":
    sr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sr.bind(('', 8091))
    sr.listen(1)
    client, addr = sr.accept()
    print 'Get connected from middleware'
disconnected = False
while True:
    if name == "v" and not disconnected:
        rs, ws, es = select.select([client], [], [], 0.1)
        for r in rs:
            try:
                msg = r.recv(4096)
                disconnected = not msg
            except:
                disconnected = True

            if r is client:
                if disconnected:
                    print 'Middleware system disconnectd.'
                    break
                else:
                    print '[Middleware msg] ', msg
    try:
        msg = repr(tuple([randint(0, 360) for x in xrange(3)]))
        ss.send(msg)
    except:
        print 'Socket close.'
        break
    time.sleep(0.1)
