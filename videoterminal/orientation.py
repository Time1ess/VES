#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-07 10:01
# Last modified: 2016-04-08 14:54
# Filename: orientation.py
# Description:
__metaclass__ = type
import mpu6050
import time
from threading import Thread


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
    __thread_status = False
    __RELATIVE_YPR = None  # This is the relative value between two MPU6050
    update_thread = None

    def __init__(self, base_addr=None, addr=None):
        self.__base_mpu = mpu6050.MPU6050(base_addr)
        self.__mpu = mpu6050.MPU6050(addr)

        self.__base_mpu.dmpInitialize()
        self.__mpu.dmpInitialize()

        self.__base_mpu.setDMPEnabled(True)
        self.__mpu.setDMPEnabled(True)

        self.__packet_size = [0, 0]
        self.__packet_size[0] = self.__base_mpu.dmpGetFIFOPacketSize()
        self.__packet_size[1] = self.__mpu.dmpGetFIFOPacketSize()

        update_thread = Thread(target=self.__update_dmp)
        update_thread.start()
        self.__thread_status = True

    def exit(self):
        """
        Set exit flag to True to terminate thread.
        """
        self.__exit = True
        time.sleep(0.1)
        if self.__thread_status is False:
            print 'Orientation update thread terminated.'
        else:
            print 'Orientation update thread still exists.'

    def get_base_ypr(self):
        """
        Get the ypr data of the base MPU6050 on Raspi.
        """
        return self.__ypr[0]

    def get_ypr(self):
        """
        Get the ypr data of the MPU6050 on the camera.
        """
        return self.__ypr[1]

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

    def __update_dmp(self):
        while True:
            if self.__exit:
                break
            # Get status
            status = [self.__base_mpu.getIntStatus(), self.__mpu.getIntStatus()]
            # check DMP data ready interrupt
            if status[0] >= 2 and status[1] >= 2:
                # get current FIFO count
                fifocounts = [self.__base_mpu.getFIFOCount(), self.__mpu.getFIFOCount()]
                # check overflow
                if fifocounts[0] == 1024:
                    self.__base_mpu.resetFIFO()
                    print 'Base MPU FIFO overflow!'
                if fifocounts[1] == 1024:
                    self.__mpu.resetFIFO()
                    print 'MPU FIFO overflow!'

                # wait for correct available data length,
                fifocounts = [self.__base_mpu.getFIFOCount(), self.__mpu.getFIFOCount()]
                while fifocounts[0] < self.__packet_size[0]:
                    fifocounts[0] = self.__base_mpu.getFIFOCount()
                while fifocounts[1] < self.__packet_size[1]:
                    fifocounts[1] = self.__mpu.getFIFOCount()

                result = [None, None]
                result[0] = self.__base_mpu.getFIFOBytes(self.__packet_size[0])
                result[1] = self.__mpu.getFIFOBytes(self.__packet_size[1])

                quaternion = [None, None]
                quaternion[0] = self.__base_mpu.dmpGetQuaternion(result[0])
                quaternion[1] = self.__mpu.dmpGetQuaternion(result[1])

                gravity = [None, None]
                gravity[0] = self.__base_mpu.dmpGetGravity(quaternion[0])
                gravity[1] = self.__mpu.dmpGetGravity(quaternion[1])

                self.__ypr[0] = self.__base_mpu.dmpGetYawPitchRoll(quaternion[0], gravity[0])
                self.__ypr[1] = self.__mpu.dmpGetYawPitchRoll(quaternion[1], gravity[1])
        self.__thread_status = False
