#!/usr/bin/python
# coding:UTF-8
# Author: David
# Email: youchen.du@gmail.com
# Created: 2016-02-27 14:53
# Last modified: 2016-02-27 18:04
# Filename: 6axis_dmp.py
# Description:
import time
import math
import mpu6050
import socket

def Check_Identity(data):
    if data == "VES":
        return True
    return False

# Sensor initialization
mpu = mpu6050.MPU6050()
mpu.dmpInitialize()
mpu.setDMPEnabled(True)
    
# get expected DMP packet size for later comparison
packetSize = mpu.dmpGetFIFOPacketSize() 

broad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
broad_sock.bind(('', 8089))
data = None
addr = None
print 'Waiting for broadcast message.'

while True:
    data, addr = broad_sock.recvfrom(4096)
    if Check_Identity(data) is True:
        break
broad_sock.close()
host = addr[0]
print 'Get broadcast message from host:', host
port = 8090

ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ss.connect((host, port))

while True:
    # Get INT_STATUS byte
    mpuIntStatus = mpu.getIntStatus()
  
    if mpuIntStatus >= 2: # check for DMP data ready interrupt (this should happen frequently) 
        # get current FIFO count
        fifoCount = mpu.getFIFOCount()
        
        # check for overflow (this should never happen unless our code is too inefficient)
        if fifoCount == 1024:
            # reset so we can continue cleanly
            mpu.resetFIFO()
            print('FIFO overflow!')
            
            
        # wait for correct available data length, should be a VERY short wait
        fifoCount = mpu.getFIFOCount()
        while fifoCount < packetSize:
            fifoCount = mpu.getFIFOCount()
        
        result = mpu.getFIFOBytes(packetSize)
        q = mpu.dmpGetQuaternion(result)
        g = mpu.dmpGetGravity(q)
        ypr = mpu.dmpGetYawPitchRoll(q, g)
        
        print(ypr['yaw'] * 180 / math.pi),
        print(ypr['pitch'] * 180 / math.pi),
        print(ypr['roll'] * 180 / math.pi)
        data = [ypr['yaw'], ypr['pitch'], ypr['roll']]
        data = map(lambda x: x*180/math.pi, data)

        try:
            msg = repr(tuple(data))
            ss.send(msg)
        except:
            print 'Socket close.'
            break
    
        # track FIFO count here in case there is > 1 packet available
        # (this lets us immediately read more without waiting for an interrupt)        
        fifoCount -= packetSize  
