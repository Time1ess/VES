#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-06 09:23
# Last modified: 2016-04-06 10:06
# Filename: ffmpeg.py
# Description:
__metaclass__ = type
import os
from const import MIDDLEWARE_PORT_VIDEO, DISPLAY_PORT_VIDEO


class FFmpeg:
    """
    A FFmpeg instance handles two ips, one is host ip,
    the other is the display terminal ip.
    After initialzied, call function `start` and the
    instance will block to start ffmpeg command.
    """

    def __init__(self, my_ip, receiver_ip, redirect):
        if redirect:
            self.__cmd = "ffmpeg -i udp://" \
            + my_ip + ":" + str(MIDDLEWARE_PORT_VIDEO) + \
            """ -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
            -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:\
            intra-refresh=1:slice-max-size=1500:keyint=30:ref=1 \
            """ + "-f mpegts udp://" + \
            receiver_ip + ":" + str(DISPLAY_PORT_VIDEO)
        else:
            self.__cmd = """ffmpeg \
            -f avfoundation -i "1" -s 1280*720 -r 30 \
            -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
            -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:intra-refresh=1:slice-max-size=1500:keyint=30:ref=1 """ + "-f mpegts udp://" + \
            receiver_ip + ":" + str(DISPLAY_PORT_VIDEO)

    def start(self):
        """
        Block to send video stream data.
        """
        os.system(self.__cmd)
