'''
communicate.py

This script handles the serial communication between the arduino and the laptop.
In the while loop, the laptop recieves a message (sensor data) from the arduino, 
feeds that data into the knn model, and then sends the alphabet prediction back
to the arduino. 

Additionally, we added checks for space and delete.
'''


# most of the code is courtesy of giobyte

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

ADD_THRESHOLD = 220
DELETE_THRESHOLD = 300
LINEAR_THRESHOLD = -0.5

ADD_COOLDOWN = 1
DELETE_COOLDOWN = 0.5

ADD_AXIS = 6
DELETE_AXIS = 7
Y_AXIS = 8

X_AXIS = 9
Z_AXIS = 10

H_THRESHOLD = 0.8


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

fn, port = read_config("data.json")
print(fn)
knn = joblib.load(fn)


ard = serial.Serial(port, 115200, timeout=5)

positions = []

delete_counter = 0
prediction = ''

prev_preds = []


while True:

    # [fingers 0 - 5, add_velocity, delete_velocity, linear_acc]
    receiveMsg = ard.readline(ard.inWaiting())     # read everything in the input buffer

    # if empty string is received or if the resulting array is malformed
    arr = receiveMsg.decode()
    arr = arr.strip().split(',')
    print(arr)

    # the array is formatted like: [fingers, add_axis, delete_axis, y_axis, x_axis, z_axis]
    if len(arr) >= 9:
        arr = np.array(arr).astype(float)
        positions.append(arr)

        # if a trigger movement is detected
        if abs(arr[ADD_AXIS]) > ADD_THRESHOLD:
            print('trigger movement detected')

            delete_counter = 0
            # take the average of all positions seen
            positions = np.array(positions)

            linear_acc = positions[-15:, Y_AXIS]


            # n.5 and (n+1).5 both round to 2 but this should not matter
            avg_pos = positions[-15:, :ADD_AXIS].mean(axis=0).round().astype(int)
            print(avg_pos)

            df = pd.DataFrame(avg_pos).T

            df.columns = ['zeroth', 'thumb', 'point', 'middle', 'ring', 'pinky']
            prediction = knn.predict(df)[0]


            if np.max(linear_acc) > LINEAR_THRESHOLD:
                if prediction == 'd':
                    prediction = 'z'
                    print(f'linear movement detected, correcting prediction (updated: {prediction})')
                elif prediction == 'i':
                    prediction = 'j'
                    print(f'linear movement detected, correcting prediction (updated: {prediction})')
            if prediction != 'z' and prediction != 'j' and len(prev_preds) >= 10:
                print(prev_preds)
                prediction = most_common(prev_preds)[0]
                # d vs z (z has linear movement)
                # i vs j (j has linear movement)
                
            # g vs l (orientation)
            # u vs v (spread fingers)
            # e vs s (kind of difficult)
            # n vs m (finger under thumb)
            # h 

            sendMsg = prediction + ',' + prediction

            # reset positions list
            positions = []
            print(sendMsg)
            print('entering cooldown, make new sign')

            # sending prediction
            sendMsg = sendMsg.encode()
            ard.write(sendMsg)

            time.sleep(ADD_COOLDOWN)

        elif abs(arr[DELETE_AXIS]) > DELETE_THRESHOLD:
            sendMsg = prediction + ',*'
            print('deleting one character')
            delete_counter += 1
            # only if delete is detected 3 times in a row, erase the whole sentence
            if delete_counter > 2:
                print('deleting whole line')
                sendMsg = prediction + ',!'
                delete_counter = 0

            print(sendMsg)

            # sending prediction
            sendMsg = sendMsg.encode()
            ard.write(sendMsg)

            time.sleep(DELETE_COOLDOWN)
        # h and g
        # if no trigger movement is detected, still make prediction
        else:
            avg_pos = np.array(positions)[-15:, :ADD_AXIS].mean(axis=0).round().astype(int)
            df = pd.DataFrame(avg_pos).astype(int).T
            # df = pd.DataFrame(arr[:ADD_AXIS]).astype(int).T

            df.columns = ['zeroth', 'thumb', 'point', 'middle', 'ring', 'pinky']
            prediction = knn.predict(df)[0]
            

            if abs(arr[X_AXIS]) > H_THRESHOLD:
                if prediction == 'u' or prediction == 'v':
                    prediction = 'h'
            if prediction == 'l':
                if abs(arr[X_AXIS]) > H_THRESHOLD:
                    prediction = 'g'
                elif abs(arr[Z_AXIS]) > H_THRESHOLD:
                    prediction = 'q'
            if prediction == 'v' and abs(arr[Z_AXIS]) > H_THRESHOLD:
                prediction = 'p'

            if len(prev_preds) <= 10:
                prev_preds.append(prediction)
            else:
                prev_preds.pop(0)
                prev_preds.append(prediction)

            sendMsg = prediction + ','
            # sending prediction
            sendMsg = sendMsg.encode()
            print(sendMsg)
            ard.write(sendMsg)

    else:
        print('got nothing')

    ard.reset_input_buffer()
    time.sleep(0.1)
