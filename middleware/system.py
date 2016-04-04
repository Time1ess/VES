#!/usr/bin/python
# coding:utf-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-04 13:29
# Last modified: 2016-04-04 15:03
# Filename: system.py
# Description:
__metaclass__ = type
from connection import Connection
from visual import Visualization
import time
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


def main():
    data_queue = Queue()
    v_msg_queue = Queue()
    c_msg_queue = Queue()
    ct = Thread(target=connection_thread, args=(data_queue, c_msg_queue))
    ct.start()
    vp = Process(target=visual_process, args=(data_queue, v_msg_queue))
    vp.start()
    ter_time = 10
    while True:
        print 'All system operational,terminate in ', ter_time, 'seconds'
        time.sleep(1)
        ter_time -= 1
        if ter_time == 0:
            v_msg_queue.put("EXIT")
            c_msg_queue.put("EXIT")
            break


if __name__ == '__main__':
    main()
