#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 11:39
# Last modified: 2016-04-10 09:34
# Filename: system.py
# Description:
__metaclass__ = type
from motor import Motor
from orientation import Orientation
from vffmpeg import VFFmpeg
from const import VIDEO_PORT_SEND, MIDDLEWARE_PORT_BROAD, VIDEO_PORT_RECEIVE
from utils import OrientationToMotorPulse
import socket
import select
from multiprocessing import Process


# global variables

def parse_message(msg):
    pass


def Check_Identity(data):
    if data == "VES":
        return True
    else:
        return False


def ffmpeg_process(v):
    # v.start()
    print 'FFmpeg process terminated.'
    return 0


def main():
    m = None
    ot = None
    v = None
    broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broad_sock.bind(('', MIDDLEWARE_PORT_BROAD))
    data = None
    addr = None
    while True:
        data, addr = broad_sock.recvfrom(4096)
        if Check_Identity(data) is True:
            break
    broad_sock.close()
    host = addr[0]
    print 'Get broadcast message from host:', host

    while True:
        try:
            m = Motor() if not m else m
            ot = Orientation(base_addr=None, addr=None) if not ot else ot
            v = VFFmpeg(host) if not v else v
            if m and ot and v:
                break
        except Exception, e:
            print '[FATAL ERROR]', e

    vp = Process(target=ffmpeg_process, args=(v))
    vp.start()
    sr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sr.bind(('', VIDEO_PORT_RECEIVE))
    sr.listen(1)

    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ss.connect((host, VIDEO_PORT_SEND))
    while True:
        rs, ws, es = select.select([sr], [], [], 0.1)
        for r in rs:
            try:
                msg = r.recv(4096)
                disconnected = not msg
            except:
                disconnected = True

            if r is sr:
                if disconnected:
                    print 'Middleware system disconnected.'
                    break
                else:
                    display_ori = parse_message(msg)
                    video_ori = ot.get_orientation()
                    pulse = OrientationToMotorPulse(display_ori, video_ori)
                    print '[Pulse set] %d' % pulse
                    # m.set_target(pulse[0], 0)
                    # m.set_target(pulse[1], 1)
        ss.send(repr(video_ori))
    vp.terminate()
    vp.join()
    sr.close()
    ss.close()

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print '[FATAL ERROR]', e
    finally:
        pass
