#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-06 09:23
# Last modified: 2016-04-11 09:49
# Filename: ffmpeg.py
# Description:
__metaclass__ = type
import os
from const import PORT_TO_REDIRECT, PORT_TO_DISPLAY


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
            + my_ip + ":" + str(PORT_TO_REDIRECT) + \
            """ -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
            -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:\
            intra-refresh=1:slice-max-size=1500:keyint=30:ref=1 \
            """ + "-f mpegts udp://" + \
            receiver_ip + ":" + str(PORT_TO_DISPLAY)
        else:
            self.__cmd = """ffmpeg \
            -f avfoundation -i "1" -s 1280*720 -r 30 \
            -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
            -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:intra-refresh=1:slice-max-size=1500:keyint=30:ref=1 """ + "-f mpegts udp://" + \
            receiver_ip + ":" + str(PORT_TO_DISPLAY)

    def start(self):
        """
        Block to send video stream data.
        """
        os.system(self.__cmd)
