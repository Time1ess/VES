#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 11:39
# Last modified: 2016-04-08 06:52
# Filename: system.py
# Description:
__metaclass__ = type
import socket
import select
import time
import re
import os
import sys
import random
from multiprocessing import Process

from motor import Motor
from orientation import Orientation
from vffmpeg import VFFmpeg
from utils import OrientationToMotorPulse

sys.path.append('..')
from const import *

threshold = 3.0
count_down = 20


def pos_valid(ot, m):
    status = [False, False]
    time.sleep(0.05)
    mpu0 = ot.get_base_ypr()
    mpu1 = ot.get_ypr()
    print mpu0, mpu1
    if (mpu1[0]+mpu0[0]) > threshold:
        m.adjust(0, False)
        print 'ADJUST motor 0 backward'
        return False
    elif (mpu1[0]+mpu0[0]) < -threshold:
        m.adjust(0, True)
        print 'ADJUST motor 0 forward'
        return False
    else:
        status[0] = True
    if (mpu1[1]-mpu0[1]) > threshold:
        m.adjust(1, True)
        print 'ADJUST motor 1 forward'
        return False
    elif (mpu1[1]-mpu0[1]) < -threshold:
        m.adjust(1, False)
        print 'ADJUST motor 1 backward'
        return False
    else:
        status[1] = True
    if status[0] and status[1]:
        print 'VALID POSITION DETECTED.', mpu0, mpu1
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
        print '[PARSE ERROR]', e
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
ss = None

def main():
    global m
    global ot
    global vp
    global ss
    global count_down
    v = None
    count_start = None


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
            if not count_start:
                count_start = time.time()
            v = VFFmpeg(host) if not v else v
            if m and ot and v:
#            if m and ot:
                break
        except Exception, e:
            print '[FATAL ERROR]', e
            exit(-1)
   

    vp = Process(target=ffmpeg_process, args=(v,))
    vp.start()

    print 'Waiting for clear bias.'
    while True:
        count_end = time.time()
        if (count_end-count_start) >= count_down:
            break
        print 'Position checking in %d second(s).' % (count_down-count_end+count_start)
        time.sleep(1)
    ot.bias[0] = ot.get_base_ypr()[0]
    ot.bias[1] = ot.get_ypr()[0]
#    print 'Begin to check position.'
#    while True:
#        if pos_valid(ot, m):
#            break
#    raw_input()

#    num1 = random.randint(50,70)
#    num2 = random.randint(-70,-50)
#    print 'Set 0 to %d' % num1
#    m.set_target(num1, 0)
#    print 'Set 1 to %d' % num2
#    m.set_target(num2, 1)
#    time.sleep(8)
#    raise Exception()



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
                    raise Exception('Middleware system disconnected.')
                else:
                    display_ori = parse_message(msg)
                    pulse = OrientationToMotorPulse(display_ori, video_ori)
                    print '[Pulse set] ',
                    print 'display:', display_ori, '\t',
                    print 'video:', video_ori, '\t',
                    print 'pulse:', pulse
                    m.set_target(pulse[0], 0)
                    m.set_target(pulse[1], 1)
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
        if ss:
            ss.close()
        while True:
            if pos_valid(ot, m):
                break
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
        if ss:
            ss.close()
        while True:
            if pos_valid(ot, m):
                break
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
