#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-06 14:13
# Last modified: 2016-04-08 13:57
# Filename: motor.py
# Description:
__metaclass__ = type
import RPi.GPIO as GPIO
import threading
import time
import sys
from random import randint


class Motor:
    """
    A instance of Motor class handles two threads, to simultaneously
    control the rolling of the two motors.
    """
    __exit = False
    __delay = 5/1000.0
    __current_pos = [0, 0]
    __target_pos = [0, 0]
    __threads = [None, None]
    __threads_status = [False, False]

    def __init__(self):
        """
        Do initialization and prepares for motors.
        """

        # Use BCM coding mode.
        GPIO.setmode(GPIO.BCM)

        # enable PIN set
        self.__enable_pin = 18

        # Motor PIN set
        # TODO: Optional PIN set
        self.__M1_I1_pin = 4
        self.__M1_I2_pin = 17
        self.__M1_I3_pin = 24
        self.__M1_I4_pin = 23

        self.__M2_I1_pin = 19
        self.__M2_I2_pin = 26
        self.__M2_I3_pin = 21
        self.__M2_I4_pin = 20

        # GPIO setup
        GPIO.setwarnings(False)
        GPIO.setup(self.__enable_pin, GPIO.OUT)
        GPIO.setup(self.__M1_I1_pin, GPIO.OUT)
        GPIO.setup(self.__M1_I2_pin, GPIO.OUT)
        GPIO.setup(self.__M1_I3_pin, GPIO.OUT)
        GPIO.setup(self.__M1_I4_pin, GPIO.OUT)
        GPIO.setup(self.__M2_I1_pin, GPIO.OUT)
        GPIO.setup(self.__M2_I2_pin, GPIO.OUT)
        GPIO.setup(self.__M2_I3_pin, GPIO.OUT)
        GPIO.setup(self.__M2_I4_pin, GPIO.OUT)

        # enable PIN enable

        GPIO.output(self.__enable_pin, 1)

        self.__threads[0] = threading.Thread(target=self.__M1_thread)
        self.__threads[0].start()
        self.__threads_status[0] = True
        print 'M1 thread created.'
        self.__threads[1] = threading.Thread(target=self.__M2_thread)
        self.__threads[1].start()
        self.__threads_status[1] = True
        print 'M2 thread created.'

    def __forward(self, index):
        delay = self.__delay
        if index == 0:
            setStep = self.__setStep_1
        else:
            setStep = self.__setStep_2
        setStep(1, 0, 1, 0)
        time.sleep(delay)
        setStep(0, 1, 1, 0)
        time.sleep(delay)
        setStep(0, 1, 0, 1)
        time.sleep(delay)
        setStep(1, 0, 0, 1)
        time.sleep(delay)

    def __backward(self, index):
        delay = self.__delay
        if index == 0:
            setStep = self.__setStep_1
        else:
            setStep = self.__setStep_2
        setStep(1, 0, 0, 1)
        time.sleep(delay)
        setStep(0, 1, 0, 1)
        time.sleep(delay)
        setStep(0, 1, 1, 0)
        time.sleep(delay)
        setStep(1, 0, 1, 0)
        time.sleep(delay)

    def __M1_thread(self):
        current = self.__current_pos[0]
        last_target = -1
        while True:
            if self.__exit:
                break
            target = self.__target_pos[0]
            if last_target != target:
                last_target = target
                print '[M1]\t', current, '\t', target
            if target == current:
                time.sleep(0.02)
            elif target > current:
                self.__forward(0)
                current += 1
            else:
                self.__backward(0)
                current -= 1
        print 'M1 thread terminated.'
        self.__threads_status[0] = False

    def __M2_thread(self):
        current = self.__current_pos[1]
        last_target = -1
        while True:
            if self.__exit:
                break
            target = self.__target_pos[1]
            if last_target != target:
                last_target = target
                print '[M2]\t', current, '\t', target
            if target == current:
                time.sleep(0.02)
            elif target > current:
                self.__forward(1)
                current += 1
            else:
                self.__backward(1)
                current -= 1
        print 'M2 thread terminated.'
        self.__threads_status[1] = False

    def adjust(self, index, forward):
        """
        Rotate the motor to make Orientation to be (0, 0).
        Warning: Only use this in initialize the orientation.
        """
        if forward:
            self.__forward(index)
        else:
            self.__backward(index)

    def __setStep_1(self, w1, w2, w3, w4):
        GPIO.output(self.__M1_I1_pin, w1)
        GPIO.output(self.__M1_I2_pin, w2)
        GPIO.output(self.__M1_I3_pin, w3)
        GPIO.output(self.__M1_I4_pin, w4)

    def __setStep_2(self, w1, w2, w3, w4):
        GPIO.output(self.__M2_I1_pin, w1)
        GPIO.output(self.__M2_I2_pin, w2)
        GPIO.output(self.__M2_I3_pin, w3)
        GPIO.output(self.__M2_I4_pin, w4)

    def set_target(self, pos, index):
        """
        Set target with pos and index, the motor thread will detect this change
        and will automatically prepare for next motor rolling.
        """
        self.__target_pos[index] = pos

    def exit(self):
        """
        Set exit flag to True and all threads will detect this change and exit,
        then this function will notify user exit status.
        """
        self.__exit = True
        time.sleep(0.1)
        if reduce(lambda x,y :x or y, self.__threads_status) is False:
            print 'All motor threads terminated.'
        else:
            print 'Motor thread still exists.'



def main(m):
    i = 0
    try:
        while True:
            i += 1
            if i == 100:
                m.exit()
                break
            target = [randint(-200, 200) for x in xrange(2)]
            m.set_target(target[0], 0)
            m.set_target(target[1], 1)
            time.sleep(0.1)
    except KeyboardInterrupt:
        m.exit()
        raise Exception("KeyboardInterrupt")

if __name__ == '__main__':
    m = Motor()
    try:
        main(m)
    except Exception,e:
        print 'Error:',e
        print 'All exit.'

