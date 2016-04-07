#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 11:39
# Last modified: 2016-04-07 11:42
# Filename: system.py
# Description:
__metaclass__ = type
from motor import Motor
from orientation import Orientation
from vffmpeg import VFFmpeg
import time
import os
from threading import Thread
from multiprocessing import Process, Queue


def main():
    pass

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print '[FATAL ERROR]', e
    finally:
        pass
