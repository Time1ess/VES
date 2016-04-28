#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 11:39
# Last modified: 2016-04-07 22:40
# Filename: system.py
# Description:
__metaclass__ = type
from motor import Motor
from orientation import Orientation
from vffmpeg import VFFmpeg
from const import PORT_FROM_VIDEO, PORT_TO_BROADCAST, PORT_TO_VIDEO
from utils import OrientationToMotorPulse
import socket
import select
import re
import os
from multiprocessing import Process


threshold = 400.0


def pos_valid(ot, m):
    status = [False, False]
    video_ori = ot.get_orientation()
    print '[INITIALIZATION ORIENTATION]', video_ori
    if video_ori[0] > threshold:
        m.adjust(0, False)
        print 'ADJUST motor 0 backward'
        return False
    elif video_ori[0] < -threshold:
        m.adjust(0, True)
        print 'ADJUST motor 0 forward'
        return False
    else:
        status[0] = True
    if video_ori[1] > threshold:
        m.adjust(1, False)
        print 'ADJUST motor 1 backward'
        return False
    elif video_ori[1] < -threshold:
        m.adjust(1, True)
        print 'ADJUST motor 1 forward'
        return False
    else:
        status[1] = True
    if status[0] and status[1]:
        print 'VALID POSITION DETECTED.', video_ori
        return True
    return False


def parse_message(msg):
    if not msg:
        return None
    try:
        data = re.match(r'\((.*?)\)', msg)
        data = re.sub(r',', '', data.group(1))
        data = data.split(' ')
        data = map(lambda x: int(float(x)), data)
        return data
    except Exception,e:
        print '[PARSE ERROR]',e
        return None


def Check_Identity(data):
    if data == "VES":
        return True
    else:
        return False


def ffmpeg_process(v):
    v.start()
    print 'FFmpeg process terminated.'
    return 0

m = None
ot = None
vp = None

def main():
    global m
    global ot
    global vp
    v = None

    broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broad_sock.bind(('', PORT_TO_BROADCAST))
    data = None
    addr = None
    print 'Wait for broadcast message.'
    while True:
        data, addr = broad_sock.recvfrom(4096)
        if Check_Identity(data) is True:
            break
    broad_sock.close()
    host = addr[0]
    print 'Get broadcast message from host:', host

    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ss.connect((host, PORT_FROM_VIDEO))

    sr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sr.bind(('', PORT_TO_VIDEO))
    sr.listen(1)
    md, addr = sr.accept()
    
    print 'Start to instantiate classes.'
    while True:
        try:
            m = Motor() if not m else m
            ot = Orientation() if not ot else ot
            v = VFFmpeg(host) if not v else v
            if m and ot and v:
                break
        except Exception, e:
            print '[FATAL ERROR]', e
            exit(-1)

    while True:
        if pos_valid(ot, m):
            break

    vp = Process(target=ffmpeg_process, args=(v,))
    vp.start()

    print 'Start main loop.'
    while True:
        video_ori = ot.get_orientation()
        rs, ws, es = select.select([md], [], [], 0.1)
        for r in rs:
            try:
                msg = r.recv(4096)
                disconnected = not msg
            except:
                disconnected = True

            if r is md:
                if disconnected:
                    print 'Middleware system disconnected.'
                    break
                else:
                    display_ori = parse_message(msg)
                    pulse = OrientationToMotorPulse(display_ori, video_ori)
                    # print '[Pulse set] ',
                    # print 'display:', display_ori, '\t',
                    # print 'video:', video_ori, '\t',
                    # print 'pulse:', pulse
                    # m.set_target(pulse[0], 0)
                    # m.set_target(pulse[1], 1)
        ss.send(str(video_ori))
    m.exit()
    vp.terminate()
    vp.join()
    sr.close()
    ss.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'EXIT SIGNAL DETECTED.'
        if m:
            m.exit()
        if ot:
            ot.exit()
        if vp:
            vp.terminate()
            os.system('sudo killall -9 raspivid')
            os.system('sudo killall -9 ffmpeg')
            vp.join()
    except Exception, e:
        print '[FATAL ERROR]', e
        if m:
            m.exit()
        if ot:
            ot.exit()
        if vp:
            vp.terminate()
            os.system('sudo killall -9 raspivid')
            os.system('sudo killall -9 ffmpeg')
            vp.join()
    finally:
        pass
