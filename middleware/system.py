#!/usr/bin/python
# coding:utf-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-04 13:29
# Last modified: 2016-04-04 17:11
# Filename: system.py
# Description:
__metaclass__ = type
from connection import Connection
from visual import Visualization
import time
import os
from threading import Thread
from multiprocessing import Process, Queue

threads = {}


def visual_process(data_queue, msg_queue):
    v = Visualization()
    v.run(data_queue, msg_queue)
    print 'Visual process terminated.'
    return 0


def connection_thread(data_queue, msg_queue):
    con = Connection()
    con.broad_to_connect()
    con.start_data_process(data_queue, msg_queue)
    print 'Connection thread terminated.'
    return 0


def ffmpeg_process(ip):
    cmd = """ffmpeg -i udp://192.168.1.105:6665
    -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p
    -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:intra-refresh=1:
    slice-max-size=1500:keyint=30:ref=1
    -f mpegts udp://192.168.1.114:8093"""
    cmd2 = """ffmpeg \
    -f avfoundation -i "1" -s 1280*720 -r 30 \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:intra-refresh=1:slice-max-size=1500:keyint=30:ref=1 \
    -f mpegts udp://192.168.1.102:8093"""
    os.system(cmd2)
    print 'FFmpeg process terminated.'
    return 0

data_queue = None
v_msg_queue = None
c_msg_queue = None
ct = None
vp = None
fp = None


def terminate():
    global data_queue
    global v_msg_queue
    global c_msg_queue
    global ct
    global vp
    global fp
    os.system("pkill ffmpeg")
    v_msg_queue.put("EXIT")
    c_msg_queue.put("EXIT")
    vp.terminate()
    vp.join()
    fp.terminate()
    fp.join()
    print 'Middleware System shutdown.'
    exit(0)


def main():
    global data_queue
    data_queue = Queue()
    global v_msg_queue
    v_msg_queue = Queue()
    global c_msg_queue
    c_msg_queue = Queue()
    global ct
    ct = Thread(target=connection_thread, args=(data_queue, c_msg_queue))
    ct.start()
    global vp
    vp = Process(target=visual_process, args=(data_queue, v_msg_queue))
    vp.start()
    global fp
    fp = Process(target=ffmpeg_process, args=("",))
    fp.start()
    ter_time = 20
    while True:
        print 'All system operational,terminate in ', ter_time, 'seconds'
        time.sleep(1)
        ter_time -= 1
        if ter_time == 0:
            return


if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print '[FATAL ERROR]', e
        terminate()
    finally:
        terminate()
