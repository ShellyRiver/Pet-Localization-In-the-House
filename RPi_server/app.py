import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template
import numpy as np

app = Flask(__name__)

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

# Features obtained from data, used to generate website
# Including: located room of each pet of this 20 sec
#            the time percentage spent in each room of each pet over the history
analyzed_features = {
    str(PET0): {
        "room_located": -1,
        "time_spent_percentage": [-1, -1, -1, -1, -1]
    },
    str(PET1): {
        "room_located": -1,
        "time_spent_percentage": [-1, -1, -1, -1, -1]
    }
}

# Server IP and port
server_ip = '192.168.10.33'
server_port = 12345

def handle_connection(client_socket, client_address):
    raw_data = b''
    while True:
        chunk = client_socket.recv(4096)
        if not chunk:
            break
        raw_data += chunk

    client_socket.close()

    # Split the received data using the newline character as the delimiter
    data_values = raw_data.decode().split('\n')

    # Remove any empty strings from the list of data values
    data_values = [value for value in data_values if value]
    
    # Add the received data to the raw_data_list
    global raw_data_list
    raw_data_list[rooms_ip[client_address[0]]] = data_values

def receive_data(server_port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Set the SO_REUSEADDR option to solve the issue of port occupying
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((server_ip, server_port))
    server_socket.listen()

    # Create a ThreadPoolExecutor to handle multiple connections
    with ThreadPoolExecutor() as executor:
        while True:
            received_rooms = np.zeros(TOTAL_ROOMS)
            while True:
                client_socket, client_address = server_socket.accept()
                # Submit the client_socket to the thread pool
                executor.submit(handle_connection, client_socket, client_address)

                # Record the received rooms
                received_rooms[rooms_ip[client_address[0]]] = 1
                print(received_rooms)
                
                # Collecting data until data from all rooms is collected
                if np.sum(received_rooms) == TOTAL_ROOMS:
                    break

            # Analyze the combined data
            global analyzed_features, raw_data_list
            analyzed_features = analyze_data(raw_data_list)
            
            # Clear the raw data list
            raw_data_list = [[''], [''], [''], ['']]

# Helper function to analyze received data
# Compute the average rssi value for all bluetooth address in one room
# Example input: ['c9:f2:08:ec:88:19, -49;c8:a0:f1:69:d0:9c, -53;c8:a0:f1:69:d0:9c, -53;c9:f2:08:ec:88:19, -46;c8:a0:f1:69:d0:9c, -55;c9:f2:08:ec:88:19, -46;c9:f2:08:ec:88:19, -46;\r'] 
def parse_and_average_rssi(data):
    rssi_dict = {}
    count_dict = {}
    print(data)

    for item in data[0].strip().split(';'):
        if not item:
            continue
        address, rssi = item.split(',')
        rssi = int(rssi.strip())
        address = address.strip()

        if address in rssi_dict:
            rssi_dict[address] += rssi
            count_dict[address] += 1
        else:
            rssi_dict[address] = rssi
            count_dict[address] = 1

    # Calculate average RSSI for each address
    avg_rssi = {address: rssi_sum / count_dict[address] for address, rssi_sum in rssi_dict.items()}
    
    return avg_rssi

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

def analyze_data(raw_data_list):
    # Determine where is the pet based on the measurement
    pet_locations = np.full(TOTAL_PETS, -1, dtype=int)
    rssi_values = -float('inf') * np.ones(TOTAL_PETS)
    for r in range(TOTAL_ROOMS):
        avg_rssi = parse_and_average_rssi(raw_data_list[r])
        for bluetooth_addr in avg_rssi.keys():
            if bluetooth_addr in pets_address.keys() and avg_rssi[bluetooth_addr] > rssi_values[pets_address[bluetooth_addr]]:
                pet_locations[pets_address[bluetooth_addr]] = r
                rssi_values[pets_address[bluetooth_addr]] = avg_rssi[bluetooth_addr]
    
    # Determine where is the pet using HMM and update culmulated time
    global observations, total_time, time_spent
    total_time += 1   
    for pet in range(TOTAL_PETS):
        observations[pet].append(pet_locations[pet])
        pet_locations[pet] = forward_algorithm(observations[pet])
        time_spent[pet][pet_locations[pet]] += 1

    # Fill in analyzed features
    analyzed_features = {}
    for pet in range(TOTAL_PETS):
        analyzed_features[str(pet)] = {
            "room_located": int(pet_locations[pet]),
            "time_spent_percentage": [t / total_time for t in time_spent[pet]]
        }
    print(analyzed_features)

    return analyzed_features

# dummy data for testing the website
analyzed_features = {
    str(PET0): {
        "room_located": 1,
        "time_spent_percentage": [0.3, 0.3877, 0.1123, 0, 0.2]
    },
    str(PET1): {
        "room_located": 0,
        "time_spent_percentage": [0.33333, 0.3333, 0.3333, 0.1333, 0.2]
    }
}

@app.route('/')
def index():
    global analyzed_features
    
    return render_template('index.html', data=analyzed_features)

if __name__ == '__main__':
    data_receiver_thread = threading.Thread(target=receive_data, args=(server_port,))
    data_receiver_thread.daemon = True
    data_receiver_thread.start()

    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
