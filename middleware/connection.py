#!/usr/bin/python
# coding:UTF-8
__metaclass__ = type
import socket
import select


class Connection:
    """
    class Connection is for broadcasting msg to get terminals connected.
    port usage:
        broad_port = 8089
        video_port_g = 8090
        video_port_s = 8091
        display_port_g = 8092
    """
    broad_host = '<broadcast>'
    broad_port = 8089  # port for broadcasting msg to all terminals
    broad_addr = (broad_host, broad_port)
    host = ''
    video_port_g = 8090  # port for receiving gyro data from video terminal
    video_port_s = 8091  # port for sending motor cmd to video terminal
    display_port_g = 8092  # port for receiving gyro data from display terminal
    exit = False

    def __init__(self):
        """
        Set up broadcast socket, video terminal socket, display terminal socket
        """
        # Set up broadcast socket
        self.broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broad_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broad_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broad_sock.bind(('', 0))

        # Prepare video terminal socket
        print 'Prepare video terminal socket.'
        self.video_terminal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.video_terminal.bind((self.host, self.video_port_g))
        self.video_terminal.listen(1)

        # Prepare display terminal socket
        print 'Prepare display terminal socket.'
        self.display_terminal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.display_terminal.bind((self.host, self.display_port_g))
        self.display_terminal.listen(1)

        self.waits = [self.video_terminal, self.display_terminal]
        self.readys = {}
        self.readys['display'] = None
        self.readys['video'] = None

    def broad_to_connect(self):
        """
        Broadcast msg to all terminals,and wait for response.
        """
        print 'Start broadcasting.'
        while True:
            if self.readys['display'] and self.readys['video']:
                break
            self.broad_sock.sendto("VES", self.broad_addr)
            rs, ws, es = select.select(self.waits, [], [], 3)
            for r in rs:
                if r is self.video_terminal:
                    client, addr = self.video_terminal.accept()
                    print 'Video terminal get connection from', addr
                    self.readys['video'] = client
                elif r is self.display_terminal:
                    client, addr = self.display_terminal.accept()
                    print 'Display terminal get connection from', addr
                    self.readys['display'] = client
                else:
                    print 'Unknown terminal.'
        print 'All terminal ports are ready.'

    def start_data_process(self):
        """
        Begin to receive or send data over tcp link.
        """
        while True:
            if self.exit:
                self.terminate()
                print 'System shutdown.'
                break
            rs, ws, es = select.select(self.readys.values(), [], [], 3)
            for r in rs:
                try:
                    msg = r.recv(4096)
                    disconnected = not msg
                except:
                    disconnected = True

                if r is self.readys['video']:
                    if disconnected:
                        print 'Video terminal disconnected.'
                        self.exit = True
                        del self.readys['video']
                    else:
                        print 'Get message from video   terminal:', msg
                elif r is self.readys['display']:
                    if disconnected:
                        print 'Display terminal disconnected.'
                        self.exit = True
                        del self.readys['display']
                    else:
                        print 'Get message from display terminal:', msg

    def terminate(self):
        """
        Disconnect all links, and begin memory recovery.
        """
        # Memory recovery
        print 'Begin memory recovery.'
        self.video_terminal.close()
        self.display_terminal.close()

if __name__ == "__main__":
    connection = Connection()
    connection.broad_to_connect()
    connection.start_data_process()
    print "OVER"
