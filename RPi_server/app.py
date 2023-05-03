import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template
import numpy as np
import time

app = Flask(__name__)

COLLECTING_TIME = 20

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
raw_data_list = [-1, -1, -1, -1]

# Time spent in each room
total_time = 1
time_spent = [[0, 0, 0, 0], [0, 0, 0, 0]]

# Features obtained from data, used to generate website
# Including: located room of each pet of this 20 sec
#            the time percentage spent in each room of each pet over the history
analyzed_features = {
    PET0: {
        'room_located': -1,
        'time_spent_percentage': [-1, -1, -1, -1]
    },
    PET1: {
        'room_located': -1,
        'time_spent_percentage': [-1, -1, -1, -1]
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
        start_time = time.time()
        while True:
            client_socket, client_address = server_socket.accept()
            # Submit the client_socket to the thread pool
            executor.submit(handle_connection, client_socket, client_address)

            # Collecting data for 20 seconds
            if time.time() - start_time >= COLLECTING_TIME:
                break

        # Analyze the combined data
        global analyzed_features
        analyzed_features = analyze_data(raw_data_list)

# Helper function to analyze received data
# Compute the average rssi value for all bluetooth address in one room
# Example input: ['c9:f2:08:ec:88:19, -49;c8:a0:f1:69:d0:9c, -53;c8:a0:f1:69:d0:9c, -53;c9:f2:08:ec:88:19, -46;c8:a0:f1:69:d0:9c, -55;c9:f2:08:ec:88:19, -46;c9:f2:08:ec:88:19, -46;\r'] 
def parse_and_average_rssi(data):
    rssi_dict = {}
    count_dict = {}

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

def analyze_data(raw_data_list):
    # Determine where is the pet
    pet_locations = -np.ones(TOTAL_PETS)
    rssi_values = -float('inf') * np.ones(TOTAL_PETS)
    for r in range(TOTAL_ROOMS):
        avg_rssi = parse_and_average_rssi(raw_data_list[r])
        for bluetooth_addr in avg_rssi.keys():
            if bluetooth_addr in pets_address.keys() and avg_rssi[bluetooth_addr] > rssi_values[pets_address[bluetooth_addr]]:
                pet_locations[pet_locations[bluetooth_addr]] = r

    # Update culmulated time
    global total_time, time_spent
    total_time += 1
    for pet in range(TOTAL_PETS):
        if pet_locations[pet] != OUTSIDE:
            time_spent[pet][pet_locations[pet]] += 1

    # Fill in analyzed features
    analyzed_features = {}
    for pet in range(TOTAL_PETS):
        analyzed_features[pet] = {
            'room_located': pet_locations[pet],
            'time_spent_percentage': time_spent[pet] / total_time
        }

    return analyzed_features

@app.route('/')
def index():
    global analyzed_features

    return render_template('index.html', data=analyzed_features)

if __name__ == '__main__':
    data_receiver_thread = threading.Thread(target=receive_data, args=(server_port,))
    data_receiver_thread.daemon = True
    data_receiver_thread.start()

    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)

