import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template

app = Flask(__name__)

# Room identifier
LIVING_ROOM = 0
BEDROOM_SMALL = 1
BEDROOM_LARGE = 2
BATHROOM = 3

# Pet identifier
PET0 = 0
PET1 = 1

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

# Data received from each room, each ESP32 sends data to RPi every 10 sec
raw_data_list = [-1, -1, -1, -1]

# Time spent in each room
total_time = 1
time_spent = [[0, 0, 0, 0], [0, 0, 0, 0]]

# Features obtained from data, used to generate website
# Including: located room of each pet of this 10 sec
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
    raw_data = client_socket.recv(1024)
    client_socket.close()

    # Add the received data to the raw_data_list
    global raw_data_list
    raw_data_list[rooms_ip[client_address[0]]] = raw_data.decode()

    # Analyze the combined data
    global analyzed_features
    analyzed_features = analyze_data(raw_data_list)

def receive_data(server_port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Set the SO_REUSEADDR option to solve the issue of port occupying
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((server_ip, server_port))
    server_socket.listen()

    # Create a ThreadPoolExecutor to handle multiple connections
    with ThreadPoolExecutor() as executor:
        while True:
            client_socket, client_address = server_socket.accept()
            # Submit the client_socket to the thread pool
            executor.submit(handle_connection, client_socket, client_address)


def analyze_data(raw_data_list):
    print(raw_data_list)
    print("example data: ", raw_data_list[0], type(raw_data_list[0]))

    # Update culmulated time

    total_time += 1

    # Replace this with your actual data analysis logic
    analyzed_features = 0

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

