#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 11:24
# Last modified: 2016-04-07 23:24
# Filename: vffmpeg.py
# Description:
__metaclass_ = type
import os
import sys

sys.path.append('..')
from const import *


class VFFmpeg:
    """
    A instance of class VFFmpeg handles one ip which is the middleware
    system ip.
    After initialized, call function `start` and the instance will
    block to start ffmpeg command.
    """

    def __init__(self, ip):
        self.__cmd = "raspivid -t 0 -w 1280 -h 720 -b 5000000 -vf -o - |"
        self.__cmd += "ffmpeg -i - -vcodec copy -f mpegts udp://"
        self.__cmd += ip + ":" + str(PORT_TO_REDIRECT)

    def start(self):
        """
        Block to send video stream data.
        """
        os.system(self.__cmd)
