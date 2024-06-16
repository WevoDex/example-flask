from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import requests
import threading
import urllib3
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# File to store API keys
API_KEYS_FILE = 'api_keys.txt'

# List to store API keys
api_keys = []

# Variable to keep track of the current key index
current_key_index = 0

def load_keys():
    global api_keys
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, 'r') as file:
            api_keys = [line.strip() for line in file.readlines()]

def save_keys():
    with open(API_KEYS_FILE, 'w') as file:
        for key in api_keys:
            file.write(f"{key}\n")

def get_key_balances():
    balances = []
    for idx, key in enumerate(api_keys):
        balance = get_balance(key, idx)
        balances.append(balance)
    return balances

# Function to get balance for a given API key
def get_balance(api_key, index):
    url = f"https://www.ipqualityscore.com/api/json/account/{api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return {
                'number': index + 1,
                'api_key': api_key,
                'credits': data.get('credits'),
                'usage': data.get('usage')
            }
    return {'number': index + 1, 'api_key': api_key, 'credits': 'Error', 'usage': 'Error'}

# Background thread to fetch balances periodically
def fetch_balances():
    while True:
        balances = get_key_balances()
        socketio.emit('update_balances', balances)
        time.sleep(10)  # Fetch new data every 10 seconds

@app.route('/')
def index():
    return render_template('index.html', api_keys=api_keys)

@app.route('/add_key', methods=['POST'])
def add_key():
    key = request.form['key']
    if key:
        api_keys.append(key)
        save_keys()
        socketio.emit('update_balances', get_key_balances())
    return redirect(url_for('index'))

@app.route('/add_keys_bulk', methods=['POST'])
def add_keys_bulk():
    keys = request.form['keys']
    if keys:
        for key in keys.split():
            if key:
                api_keys.append(key)
        save_keys()
        socketio.emit('update_balances', get_key_balances())
    return redirect(url_for('index'))

@app.route('/edit_key', methods=['POST'])
def edit_key():
    old_key = request.form['old_key']
    new_key = request.form['new_key']
    if old_key in api_keys:
        index = api_keys.index(old_key)
        api_keys[index] = new_key
        save_keys()
        socketio.emit('update_balances', get_key_balances())
    return redirect(url_for('index'))

@app.route('/delete_key', methods=['POST'])
def delete_key():
    key = request.form['key']
    if key in api_keys:
        api_keys.remove(key)
        save_keys()
        socketio.emit('update_balances', get_key_balances())
    return redirect(url_for('index'))

@app.route('/check_ip', methods=['GET'])
def check_ip():
    global current_key_index
    
    proxy_ip = request.args.get('proxy_ip')
    if not proxy_ip:
        return jsonify({"error": "proxy_ip parameter is required"}), 400
    
    if not api_keys:
        return jsonify({"error": "No API keys available"}), 400
    
    # Get the current API key
    api_key = api_keys[current_key_index]
    
    # Update the current key index for the next request
    current_key_index = (current_key_index + 1) % len(api_keys)
    
    # Construct the URL
    url = f"https://www.ipqualityscore.com/api/json/ip/{api_key}/{proxy_ip}"
    
    # Make the request to the IPQualityScore API
    response = requests.get(url)
    
    return jsonify(response.json())

@socketio.on('connect')
def handle_connect():
    emit('update_balances', get_key_balances())

if __name__ == '__main__':
    load_keys()
    thread = threading.Thread(target=fetch_balances)
    thread.daemon = True
    thread.start()
    socketio.run(app, port="5005", debug=True)
