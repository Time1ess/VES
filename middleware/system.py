#!/usr/bin/python
# coding:utf-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-04 13:29
# Last modified: 2016-04-13 16:16
# Filename: system.py
# Description:
__metaclass__ = type
from connection import Connection
from visual import Visualization
from ffmpeg import FFmpeg
import time
import os
from threading import Thread
from multiprocessing import Process, Queue

data_queue = None
v_msg_queue = None
c_msg_queue = None
ct = None
vp = None
fp = None
con = None


def visual_process(data_queue, msg_queue):
    v = Visualization()
    v.run(data_queue, msg_queue)
    print 'Visual process terminated.'
    return 0


def connection_thread(data_queue, msg_queue):
    global con
    con = Connection()
    con.broad_to_connect()
    fp.start()
    con.start_data_process(data_queue, msg_queue)
    print 'Connection thread terminated.'
    return 0


def ffmpeg_process(ip):
    ff = FFmpeg("0.0.0.0", con.dt_addr[0], False)
    ff.start()
    print 'FFmpeg process terminated.'
    return 0


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
    os.system("sudo killall -9 ffmpeg")
    os.system("sudo killall -9 python")
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
    ter_time = 100
    while True:
        # print 'All system operational,terminate in ', ter_time, 'seconds'
        time.sleep(1)
        # ter_time -= 1
        if ter_time == 0:
            return


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'EXIT SIGNAL DETECTED.'
        terminate()
    except Exception, e:
        print '[FATAL ERROR]', e
        terminate()
    finally:
        pass
