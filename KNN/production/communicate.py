__author__ = "So Hirota and Giovanni Bernal Ramirez"

"""
communicate.py

This script handles the serial communication between the arduino and the laptop.
In the while loop, the laptop recieves a message (sensor data) from the arduino, 
feeds that data into the knn model, and then sends the alphabet prediction back
to the arduino. 

Additionally, we added checks for space and delete.
"""

from datetime import datetime as dt
import warnings
import serial
import time
import pandas as pd
import numpy as np
import os
from sklearn.neighbors import KNeighborsClassifier
import joblib
import json
from collections import Counter

warnings.simplefilter(action='ignore', category=FutureWarning)

# DPS -> degrees per second
# G   -> earth's gravitational acceleration (9.81 m/s²)
# S   -> seconds

ADD_THRESHOLD_DPS = 220
DELETE_THRESHOLD_DPS = 300
SPACE_THRESHOLD_DPS = 220
LINEAR_THRESHOLD_G = -0.5

ADD_COOLDOWN = 1
DELETE_COOLDOWN = 0.5
SPACE_COOLDOWN = 0.5
DELETE_TIMEOUT_S = DELETE_COOLDOWN + 3

X_AXIS_DPS = 6      # space axis
Y_AXIS_DPS = 7      # append axis
Z_AXIS_DPS = 8      # delete axis

X_AXIS_G = 9
Y_AXIS_G = 10
Z_AXIS_G = 11

"""
this treshold is the fraction of earth's gravitational acceleration that projects onto the given axis a.k.a the dot product of the two vectors
if the Arduino's relative axis is perfectly parallel to earth's gravitational acceleration (pointing towards the center of the earth), 
    then the value will be 1
    
if the Arduino's relative axis is perfectly perpendicular to earth's gravitational acceleration (pointing towards the horizon),
 then the value will be 0
"""
PARALEL_AXIS_THRESHOLD_G = 0.8
t_previous = dt.now()


def read_config(filename):
    try:
        with open(filename, 'r') as file:
            config = json.load(file)
            fn_ = config["PATH"]
            port_ = config["Port"]
            return fn_, port_
    except (FileNotFoundError, KeyError) as e:
        print(f"Error reading configuration: {e}")
        return None, None
    

def most_common(lst):
    counter = Counter(lst)
    most_common_element = counter.most_common(1)[0][0]
    return most_common_element


# Note that you will need to create this data.json file
fn, port = read_config("data.json")
print(fn)
knn = joblib.load(fn)

ard = serial.Serial(port, 115200, timeout=5)

positions = []
prev_preds = []

delete_counter = 0
prediction = ''


while True:

    # [fingers 0 - 5, add_velocity, delete_velocity, linear_acc]
    receiveMsg = ard.readline(ard.inWaiting())     # read everything in the input buffer

    # if empty string is received or if the resulting array is malformed
    arr = receiveMsg.decode()
    arr = arr.strip().split(',')
    print(arr)

    # the array is formatted like: [back_of_hand, fingers, X_AXIS_DPS, Y_AXIS_DPS, Z_AXIS_DPS, X_AXIS_G, Y_AXIS_G, Z_AXIS_G]
    if len(arr) == 12:
        arr = np.array(arr).astype(float)
        positions.append(arr)

        # if a trigger movement is detected
        if abs(arr[Y_AXIS_DPS]) > ADD_THRESHOLD_DPS:
            print('trigger movement detected')

            delete_counter = 0
            t_previous = dt.now()

            positions = np.array(positions)
            linear_acc = positions[-15:, Y_AXIS_G]
            prediction = most_common(prev_preds)[0]

            if np.max(linear_acc) > LINEAR_THRESHOLD_G:
                match prediction:
                    case 'd':
                        prediction = 'z'

                    case 'i':
                        prediction = 'j'

            sendMsg = prediction + ',' + prediction

            # reset positions list
            positions = []
            print(sendMsg)
            print('entering cooldown, make new sign')

            # sending prediction
            sendMsg = sendMsg.encode()
            ard.write(sendMsg)

            time.sleep(ADD_COOLDOWN)

        elif abs(arr[Z_AXIS_DPS]) > DELETE_THRESHOLD_DPS:
            sendMsg = prediction + ',*'
            print('deleting one character')
            delete_counter += 1
            t_previous = dt.now()

            # only if delete is detected 3 times in a row, erase the whole sentence
            if delete_counter > 2:
                print('deleting whole line')
                sendMsg = prediction + ',!'
                delete_counter = 0
                t_previous = dt.now()

            print(sendMsg)

            # sending prediction
            sendMsg = sendMsg.encode()
            ard.write(sendMsg)
            time.sleep(DELETE_COOLDOWN)

        elif abs(arr[X_AXIS_DPS]) > SPACE_THRESHOLD_DPS:
            sendMsg = prediction + ', '
            print('adding space')

            print(sendMsg)

            sendMsg = sendMsg.encode()
            ard.write(sendMsg)
            time.sleep(SPACE_COOLDOWN)

        else:
            avg_pos = np.array(positions)[-15:, :6].mean(axis=0).round().astype(int)
            df = pd.DataFrame(avg_pos).astype(int).T

            df.columns = ['zeroth', 'thumb', 'point', 'middle', 'ring', 'pinky']
            prediction = knn.predict(df)[0]

            match prediction:
                case 'l':
                    if abs(arr[X_AXIS_G]) > PARALEL_AXIS_THRESHOLD_G:
                        prediction = 'g'
                    elif abs(arr[Z_AXIS_G]) > PARALEL_AXIS_THRESHOLD_G:
                        prediction = 'q'

                case 'u' | 'v' | 'k' | 'r':
                    if abs(arr[X_AXIS_G]) > PARALEL_AXIS_THRESHOLD_G:
                        prediction = 'h'

                case 'k' | 'r':
                    if not abs(arr[Y_AXIS_G]) > PARALEL_AXIS_THRESHOLD_G:
                        prediction = 'p'

            if len(prev_preds) <= 10:
                prev_preds.append(prediction)
            else:
                prev_preds.pop(0)
                prev_preds.append(prediction)

            sendMsg = prediction + ','
            sendMsg = sendMsg.encode()
            print(sendMsg)
            ard.write(sendMsg)

    else:
        print('got nothing')

    if (dt.now() - t_previous).total_seconds() > DELETE_TIMEOUT_S:
        delete_counter = 0
        t_previous = dt.now()

    ard.reset_input_buffer()
    time.sleep(0.1)
