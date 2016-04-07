#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 10:01
# Last modified: 2016-04-07 15:51
# Filename: orientation.py
# Description:
__metaclass__ = type
import mpu6050
import time
import math
from threading import Thread
import RPi.GPIO as GPIO
import os


class Orientation:
    """
    A instance of Orientation class will handle a thread to get orientation
    data continuously and calculate the current orientation of the camera
    (relative to a base mpu).
    """
    __base_mpu = None
    __mpu = None
    __exit = False
    __ypr = [None, None]
    __thread_status = [False, False]
    __RELATIVE_YPR = None  # This is the relative value between two MPU6050
    base_update_thread = None
    update_thread = None


    def __init__(self, base_addr=0x68, addr=0x69):

        print 'Orientation Instance Initializing...'
        self.__base_mpu = mpu6050.MPU6050(base_addr)
        self.__mpu = mpu6050.MPU6050(addr)

        self.__base_mpu.dmpInitialize()
        self.__mpu.dmpInitialize()

        self.__base_mpu.setDMPEnabled(True)
        self.__mpu.setDMPEnabled(True)

        self.__packet_size = [0, 0]
        self.__packet_size[0] = self.__base_mpu.dmpGetFIFOPacketSize()
        self.__packet_size[1] = self.__mpu.dmpGetFIFOPacketSize()

        base_update_thread = Thread(target=self.__update_dmp, args=(self.__base_mpu,
            self.__packet_size[0], 0))
        update_thread = Thread(target=self.__update_dmp,args=(self.__mpu,
            self.__packet_size[1], 1))
        print 'Orientation Instance Initialized...'
        update_thread.start()
        self.__thread_status[1] = True
        base_update_thread.start()
        self.__thread_status[0] = True

    def exit(self):
        """
        Set exit flag to True to terminate thread.
        """
        self.__exit = True
        time.sleep(0.5)
        if self.__thread_status[0] is False and self.__thread_status[1] is False:
            print 'Orientation update thread terminated.'
        else:
            print 'Orientation update thread still exists.'

    def get_base_ypr(self):
        """
        Get the ypr data of the base MPU6050 on Raspi.
        """
        if not self.__ypr[0]:
            return (0, 0, 0)
        base_ypr = [self.__ypr[0]['yaw'], self.__ypr[0]['pitch'], self.__ypr[0]['roll']]
        base_ypr = map(lambda x: x*180/math.pi, base_ypr)
        return base_ypr

    def get_ypr(self):
        """
        Get the ypr data of the MPU6050 on the camera.
        """
        if not self.__ypr[1]:
            return (0, 0, 0)
        ypr = [self.__ypr[1]['yaw'], self.__ypr[1]['pitch'], self.__ypr[1]['roll']]
        ypr = map(lambda x: x*180/math.pi, ypr)
        return ypr

    def get_orientation(self):
        """
        Get orientation based on the base MPU6050 sensor.
        e.g. for yaw:
            0 indicates face front
            -90 indicates face left
            90 indicated face right
        Notice:
            The difference between MPU0 and MPU1 can be described as (Y,P,R)
        when orientation of MPU0 is o_1b and orientation of MPU1 is o_2b for
        a base position. Then, although yaw is a relative value every time we
        start the system, MPU0 is always in the fixed position to the whole
        system, so we can use o_1b`(base orientation of MPU0 in the current
        session) + (Y,P,R) to get the o_2b`(base orientation of MPU1 in the
        current session).
        """
        self.__mpu_base = self.__base_mpu + self.__RELATIVE_YPR
        ot = map(lambda i: self.__mpu[i]-self.__mpu_base[i], xrange(3))
        for i in xrange(3):
            if ot[i] < -90:
                ot[i] = -90
            elif ot[i] > 90:
                ot[i] = 90
        return ot

    def __update_dmp(self, mpu, packetSize, thread_num):
        try:
            while True:
                if self.__exit:
                    break
                # Get status
                status = mpu.getIntStatus()
                if status >= 2:
                    fifoCount = mpu.getFIFOCount()
                    if fifoCount == 1024:
                        mpu.resetFIFO()
                    fifoCount = mpu.getFIFOCount()
                    while fifoCount < packetSize:
                        fifoCount = mpu.getFIFOCount()
                    result = mpu.getFIFOBytes(packetSize)
                    q = mpu.dmpGetQuaternion(result)
                    g = mpu.dmpGetGravity(q)
                    self.__ypr[thread_num] = mpu.dmpGetYawPitchRoll(q, g)
                    fifoCount -= packetSize
                    time.sleep(0.03)
        except Exception,e:
            self.__exit = True
            print '[FATAL ERROR] Error detected in orientation thread ',thread_num
            print e

        self.__thread_status[thread_num] = False
        print 'Orientation thread ',thread_num,' terminated.'

def main():
    ot = Orientation()
    now = time.time()
    mmax = -1
    delay = 0.01
    cnt = 0
    avg = 0
    try:
        while True:
            last = now
            now = time.time()
            data = ot.get_ypr()
            print '[   YPR  ] yaw:%5.2f\tpitch:%5.2f\troll:%5.2f\t' % tuple(data),
            data = ot.get_base_ypr()
            print '[BASE YPR] yaw:%5.2f\tpitch:%5.2f\troll:%5.2f\t' % tuple(data),
            mmax = now-last if now-last > mmax else mmax
            cnt += 1
            avg = (avg*(cnt-1)+now-last)/cnt
            print '[DMP TIME] cost:%.5f\tmax:%.5f\tavg:%.5f' % (now-last-delay, mmax, avg)
            time.sleep(delay)
    except KeyboardInterrupt,e:
        ot.exit()
        time.sleep(1)
    except Exception,e:
        print e
        ot.exit()
        time.sleep(1)
    print 'over'

if __name__ == '__main__':
    try:
        main()
    except Exception,e:
        print e
