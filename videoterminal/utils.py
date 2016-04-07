#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-04-08 13:58
# Last modified: 2016-04-08 07:01
# Filename: utils.py
# Description:
__metaclass__ = type
from math import ceil


def OrientationToMotorPulse(origin_display_ori, video_ori):
    """
    This function will calculate the difference between the orientation
    of display terminal and video terminal, and produce approriate motor
    command for Motor instance.
    Notice: Since the yaw angle of the head is [-90, 90] as we expected
    for example, value not in the interval will be ignored.
    """

    if origin_display_ori is None or video_ori is None:
        return (None, None)
    ANGLE_PER_PULSE = 1.4  # This is different between different motor

    display_ori = origin_display_ori

    if display_ori[0] < 180:
        display_ori[0] = -display_ori[0]
    else:
        display_ori[0] = 360-display_ori[0]

    display_ori[1] = 270-display_ori[1]


    yaw_d = display_ori[0]
    pitch_d = display_ori[1]
    yaw_v = video_ori[0]
    pitch_v = video_ori[1]

    yaw_diff = yaw_d - yaw_v
    pitch_diff = pitch_d - pitch_v - 180

    yaw_pulse = int(ceil(yaw_diff / ANGLE_PER_PULSE))
    pitch_pulse = int(ceil(pitch_diff / ANGLE_PER_PULSE))

    return (yaw_pulse, pitch_pulse)
