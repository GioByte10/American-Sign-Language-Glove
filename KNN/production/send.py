'''
script to test out serial communication
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

warnings.simplefilter(action='ignore', category=FutureWarning)

ADD_THRESHOLD = 300
DELETE_THRESHOLD = 300
LINEAR_THRESHOLD = 300

ADD_COOLDOWN = 3
DELETE_COOLDOWN = 1

ADD_AXIS = 6
DELETE_AXIS = 7
LINEAR_AXIS = 8


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


fn, port = read_config("/Users/so/Documents/projects/asl-detection/production/data.json")
print(fn)
knn = joblib.load(fn)


ard = serial.Serial(port, 115200, timeout=5)

positions = []
delete_counter = 0
prediction = ''


while True:

    a = 'a,'.encode()

    ard.write(a)
    print(a)
    time.sleep(0.2)
