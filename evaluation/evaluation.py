import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template
import numpy as np

# Evaluate the accuracy of HMM over use average data only

# Room identifier
LIVING_ROOM = 0
BEDROOM_SMALL = 1
BEDROOM_LARGE = 2
BATHROOM = 3
OUTSIDE = -1

TOTAL_ROOMS = 4

# Pet identifier
PET0 = 0
PET1 = 1

TOTAL_PETS = 2

# Global variables to store the raw and analyzed data
# Map IP address of ESP32 to room identifier 
rooms_ip = {
    '192.168.10.100': LIVING_ROOM,
    '192.168.10.101': BEDROOM_SMALL,
    '192.168.10.102': BEDROOM_LARGE,
    '192.168.10.103': BATHROOM
}

# Map bluetooth address to pet identifier
pets_address = {
    'c8:a0:f1:69:d0:9c': PET0,   # the white tag
    'c9:f2:08:ec:88:19': PET1    # the black one
}

# Data received from each room, each ESP32 sends data to RPi every 20 sec
raw_data_list = [[''], [''], [''], ['']]

# Time spent in each room
total_time = 0
time_spent = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]

observations = [[], []]

# Use Hidden Markov Model to improve accuracy
# O: observations
# model: - A, the state transition probability matrix of size N x N, where N represents the number of hidden states(or true states).
#        - B, the observation probability matrix of size N x M, where M represents the number of observed states. Here, M = N.
#        - pi, an initial distribution vector of size 1 x N
def forward_algorithm(O):
    model = {
        'A': np.array([[0.8, 0.12, 0.03, 0.045, 0.005],   # from living room to other rooms
                       [0.12,  0.8, 0.03, 0.045, 0.005],   # from small bedroom to other rooms
                       [0.23, 0.14, 0.5, 0.11, 0.02],   # from large bedroom to other rooms
                       [0.4, 0.24, 0.05, 0.3,  0.01],   # from bathroom to other rooms
                       [0.15, 0.02, 0.02, 0.01, 0.8]]), # from outside to each rooms
        'B': np.array([[0.85, 0.02, 0.02, 0.1, 0.01],
                       [0.15, 0.8, 0, 0.05, 0],
                       [0.0625, 0, 0.9, 0.0375, 0],
                       [0.025, 0, 0.013, 0.95, 0.012],
                       [0.05, 0, 0.05, 0, 0.9]]),
        'pi': np.array([0.4, 0.4, 0.09, 0.1, 0.01])
    }

    max_len = 30 # set the max length of observation to avoid being too long
    num_states = model['A'].shape[0]
    if len(O) > max_len:
        O = O[-max_len:]
    num_obs = len(O)
    
    # Initialization
    alpha = np.zeros((num_states, num_obs))
    alpha[:, 0] = model['pi'] * model['B'][:, O[0]]
    
    # Recursion
    for t in range(1, num_obs):
        for j in range(num_states):
            alpha[j, t] = model['B'][j, O[t]] * np.sum(alpha[:, t-1] * model['A'][:, j])

    # Return the most likely hidden state at the last time step
    time_step = alpha.shape[1] - 1
    return np.argmax(alpha[:, time_step])

def analyze_data(data_list):
    # Determine where is the pet based on the measurement
    pet_locations = np.full(TOTAL_PETS, -1, dtype=int)
    rssi_values = -float('inf') * np.ones(TOTAL_PETS)
    for r in range(TOTAL_ROOMS):
        avg_rssi = data_list[r]
        for bluetooth_addr in avg_rssi.keys():
            if bluetooth_addr in pets_address.keys() and avg_rssi[bluetooth_addr] > rssi_values[pets_address[bluetooth_addr]]:
                pet_locations[pets_address[bluetooth_addr]] = r
                rssi_values[pets_address[bluetooth_addr]] = avg_rssi[bluetooth_addr]
    average_locations = pet_locations.copy()

    # Determine where is the pet using HMM and update culmulated time
    global observations, total_time, time_spent
    total_time += 1   
    for pet in range(TOTAL_PETS):
        observations[pet].append(pet_locations[pet])
        pet_locations[pet] = forward_algorithm(observations[pet])
        time_spent[pet][pet_locations[pet]] += 1
    HMM_locations = pet_locations.copy()

    return average_locations, HMM_locations
def read_rssi_data(file_name):
    with open(file_name, 'r') as file:
        lines = file.readlines()

    data = []
    current_room = -1
    set_data = {} # data from all 4 rooms
    room_data = {}

    for line in lines:
        line = line.strip()

        if line.isdigit():
            if current_room != -1:
                set_data[current_room] = room_data
                room_data = {}
                if current_room == 3:
                    data.append(set_data)
                    set_data = {}

            current_room = int(line)
        else:
            address, rssi = line.split(',')
            room_data[address] = float(rssi)

    set_data[current_room] = room_data
    data.append(set_data)

    return data

if __name__ == '__main__':
    file_name0 = "average_rssi_value0.txt" # Pet0 is in living room, pet1 is in bathroom
    file_name1 = "average_rssi_value1.txt" # Pet0 is in small bedroom, pet1 is in large bedroom

    data0 = read_rssi_data(file_name0)
    data1 = read_rssi_data(file_name1)

    groundtruth0 = [0, 3]
    groundtruth1 = [1, 2]

    # Evaluate from data0
    n0 = len(data0)
    average_true_count0 = [0, 0]
    HMM_true_count0 = [0, 0]
    for i in range(n0):
        average_locations, HMM_locations = analyze_data(data0[i])
        for j in range(2):
            if average_locations[j] == groundtruth0[j]:
                average_true_count0[j] += 1
            if HMM_locations[j] == groundtruth0[j]:
                HMM_true_count0[j] += 1

    # Evaluate from data1
    n1 = len(data1)
    average_true_count1 = [0, 0]
    HMM_true_count1 = [0, 0]
    for i in range(n1):
        average_locations, HMM_locations = analyze_data(data1[i])
        for j in range(2):
            if average_locations[j] == groundtruth1[j]:
                average_true_count1[j] += 1
            if HMM_locations[j] == groundtruth1[j]:
                HMM_true_count1[j] += 1

    accuracy_average = [average_true_count0[0] / n0, average_true_count1[0] / n1, average_true_count1[1] / n1, average_true_count0[1] / n0]
    accuracy_HMM = [HMM_true_count0[0] / n0, HMM_true_count1[0] / n1, HMM_true_count1[1] / n1, HMM_true_count0[1] / n0]

    print(accuracy_average, np.average(accuracy_average), accuracy_HMM, np.average(accuracy_HMM))
