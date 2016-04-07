#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-08 05:38
# Last modified: 2016-04-08 05:43
# Filename: adjust.py
# Description:

import sys
import time

from motor import Motor


try:
    index = int(sys.argv[1])
    rot = True if sys.argv[2] == '1' else False
    num = int(sys.argv[3])

    m = Motor()
    
    for i in xrange(num):
        m.adjust(index, rot)
        time.sleep(0.08)
    
    m.exit()
except Exception, e:
    print 'ERROR:', e
except KeyboardInterrupt, e:
    print 'EXIT.'

