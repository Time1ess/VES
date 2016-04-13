#!/usr/bin/python
# coding:utf-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-04 13:30
# Last modified: 2016-04-13 14:47
# Filename: connection.py
# Description:
__metaclass__ = type
import socket
import select
import re
from const import PORT_TO_BROADCAST, PORT_FROM_DISPLAY
from const import PORT_TO_VIDEO, PORT_FROM_VIDEO


class Connection:
    """
    class Connection is for broadcasting msg to get terminals connected.
    port usage:
        __broad_port = 8089
        __vp_g = 8090
        __vp_s = 8091
        __dp_g = 8092
    """
    __broad_host = '<broadcast>'
    __broad_addr = (__broad_host, PORT_TO_BROADCAST)
    __host = ''
    __exit = False
    __v_yp = [0, 0]
    __d_yp = [0, 0]
    __data_queue = None
    __msg_queue = None
    vt_addr = None
    dt_addr = None

    def get_yw_data(self):
        return (self.__v_yp, self.__d_yp)

    def parse_data(self, data):
        if not data:
            return None
        try:
            data = re.match(r'\((.*?)\)', data)
            data = re.sub(r',', '', data.group(1))
            data = data.split(' ')
            data = map(lambda x: float(x), data)
            return data[:2]
        except:
            return None

    def __init__(self):
        """
        Set up broadcast socket, video terminal socket, display terminal socket
        """
        # Set up broadcast socket
        self.__broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__broad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__broad.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__broad.bind(('', 0))

        # Prepare video terminal socket
        print 'Prepare video terminal socket.'
        self.__vt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__vt.bind((self.__host, PORT_FROM_VIDEO))
        self.__vt.listen(1)

        self.__vt_g = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Prepare display terminal socket
        print 'Prepare display terminal socket.'
        self.__dt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__dt.bind((self.__host, PORT_FROM_DISPLAY))
        self.__dt.listen(1)

        self.__waits = [self.__vt, self.__dt]
        self.__readys = {}
        self.__readys['display'] = None
        self.__readys['video'] = None

    def broad_to_connect(self):
        """
        Broadcast msg to all terminals,and wait for response.
        """
        print 'Start broadcasting.'
        while True:
            if self.__readys['display'] and self.__readys['video']:
                break
            self.__broad.sendto("VES", self.__broad_addr)
            rs, ws, es = select.select(self.__waits, [], [], 3)
            for r in rs:
                if r is self.__vt:
                    client, addr = self.__vt.accept()
                    print 'Video terminal get connection from', addr
                    self.vt_addr = addr
                    self.__readys['video'] = client
                    self.__vt_g.connect((addr[0], PORT_TO_VIDEO))
                elif r is self.__dt:
                    client, addr = self.__dt.accept()
                    print 'Display terminal get connection from', addr
                    self.dt_addr = addr
                    self.__readys['display'] = client
                else:
                    print 'Unknown terminal.'
        print 'All terminal ports are ready.'

    def start_data_process(self, data_queue, msg_queue):
        """
        Begin to receive or send data over tcp link.
        """
        if not self.__data_queue:
            self.__data_queue = data_queue
            self.__msg_queue = msg_queue
        while True:
            try:
                msg = self.__msg_queue.get(block=False)
                if msg == "EXIT":
                    self.__exit = True
            except:
                pass
            if self.__exit:
                self.__terminate()
                print 'Connection shutdown.'
                break
            if not self.__readys['display'] or not self.__readys['video']:
                self.broad_to_connect()
            rs, ws, es = select.select(self.__readys.values(), [], [], 3)
            for r in rs:
                try:
                    msg = r.recv(4096)
                    disconnected = not msg
                except:
                    disconnected = True

                if r is self.__readys['video']:
                    if disconnected:
                        print 'Video terminal disconnected.'
                        self.__readys['video'] = None
                    else:
                        # print 'Get message from video   terminal:', msg
                        data = self.parse_data(msg)
                        self.__data_queue.put([None, data])
                elif r is self.__readys['display']:
                    if disconnected:
                        print 'Display terminal disconnected.'
                        self.__readys['display'] = None
                    else:
                        # print 'Get message from display terminal:', msg
                        data = self.parse_data(msg)
                        self.__data_queue.put([data, None])
                        self.__vt_g.send(repr(tuple(data)))

    def __terminate(self):
        """
        Disconnect all links, and begin memory recovery.
        """
        # Memory recovery
        self.__vt.close()
        self.__dt.close()

    def set_exit(self, exit):
        self.__exit = exit

if __name__ == "__main__":
    connection = Connection()
    connection.broad_to_connect()
    connection.start_data_process()
    print "OVER"
