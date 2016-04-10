#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-08 13:58
# Last modified: 2016-04-08 14:31
# Filename: utils.py
# Description:
__metaclass__ = type
from math import ceil


def OrientationToMotorPulse(display_ori, video_ori):
    """
    This function will calculate the difference between the orientation
    of display terminal and video terminal, and produce approriate motor
    command for Motor instance.
    Notice: Since the yaw angle of the head is [-90, 90] as we expected
    for example, value not in the interval will be ignored.
    """
    ANGLE_PER_PULSE = 1.4  # This is different between different motor

    if display_ori[1] < -90:
        yaw_d = -90
    elif display_ori > 90:
        yaw_d = 90
    else:
        yaw_d = display_ori[0]
    if display_ori[1] < -90:
        pitch_d = -90
    elif display_ori[1] > 90:
        pitch_d = 90
    else:
        pitch_d = display_ori[1]
    yaw_v = video_ori[0]
    pitch_v = display_ori[1]

    yaw_diff = yaw_d - yaw_v
    pitch_diff = pitch_d - pitch_v

    yaw_pulse = int(ceil(yaw_diff / ANGLE_PER_PULSE))
    pitch_pulse = int(ceil(pitch_diff / ANGLE_PER_PULSE))

    return (yaw_pulse, pitch_pulse)
