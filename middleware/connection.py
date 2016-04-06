#!/usr/bin/python
# coding:utf-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-04 13:30
# Last modified: 2016-04-06 09:56
# Filename: connection.py
# Description:
__metaclass__ = type
import socket
import select
import re
from const import MIDDLEWARE_PORT_BROAD, DISPLAY_PORT_RECEIVE
from const import VIDEO_PORT_SEND, VIDEO_PORT_RECEIVE


class Connection:
    """
    class Connection is for broadcasting msg to get terminals connected.
    port usage:
        __broad_port = 8089
        __video_port_g = 8090
        __video_port_s = 8091
        __display_port_g = 8092
    """
    __broad_host = '<broadcast>'
    __broad_port = MIDDLEWARE_PORT_BROAD
    __broad_addr = (__broad_host, __broad_port)
    __host = ''
    __video_port_g = VIDEO_PORT_RECEIVE
    __video_port_s = VIDEO_PORT_SEND
    __display_port_g = DISPLAY_PORT_RECEIVE
    __exit = False
    __v_yp = [0, 0]
    __d_yp = [0, 0]
    __data_queue = None
    __msg_queue = None
    video_terminal_addr = None
    display_terminal_addr = None

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
        self.__broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__broad_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__broad_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__broad_sock.bind(('', 0))

        # Prepare video terminal socket
        print 'Prepare video terminal socket.'
        self.__video_terminal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__video_terminal.bind((self.__host, self.__video_port_g))
        self.__video_terminal.listen(1)

        # Prepare display terminal socket
        print 'Prepare display terminal socket.'
        self.__display_terminal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__display_terminal.bind((self.__host, self.__display_port_g))
        self.__display_terminal.listen(1)

        self.__waits = [self.__video_terminal, self.__display_terminal]
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
            self.__broad_sock.sendto("VES", self.__broad_addr)
            rs, ws, es = select.select(self.__waits, [], [], 3)
            for r in rs:
                if r is self.__video_terminal:
                    client, addr = self.__video_terminal.accept()
                    print 'Video terminal get connection from', addr
                    self.video_terminal_addr = addr
                    self.__readys['video'] = client
                elif r is self.__display_terminal:
                    client, addr = self.__display_terminal.accept()
                    print 'Display terminal get connection from', addr
                    self.display_terminal_addr = addr
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
                        self.__data_queue.put([None, self.parse_data(msg)])
                elif r is self.__readys['display']:
                    if disconnected:
                        print 'Display terminal disconnected.'
                        self.__readys['display'] = None
                    else:
                        # print 'Get message from display terminal:', msg
                        self.__data_queue.put([self.parse_data(msg), None])

    def __terminate(self):
        """
        Disconnect all links, and begin memory recovery.
        """
        # Memory recovery
        self.__video_terminal.close()
        self.__display_terminal.close()

    def set_exit(self, exit):
        self.__exit = exit

if __name__ == "__main__":
    connection = Connection()
    connection.broad_to_connect()
    connection.start_data_process()
    print "OVER"
