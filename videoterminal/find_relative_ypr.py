#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-08 01:27
# Last modified: 2016-04-08 06:05
# Filename: find_relative_ypr.py
# Description:

from orientation import Orientation
import time


bias_set = False
ot = Orientation()

start = time.time()
try:
    while True:
        now = time.time()
        print '[%5.2f]' % (now-start),
        if now-start > 20 and not bias_set:
            ot.bias[0] = ot.get_base_ypr()[0]
            ot.bias[1] = ot.get_ypr()[0]
            bias_set = True
        print ot.get_base_ypr(), ot.get_ypr(), ot.get_orientation(False)
except KeyboardInterrupt:
    ot.exit()
finally:
    ot.exit()
