from flask import Flask, render_template, request, flash, redirect, url_for,Response,jsonify
import mysql.connector
from drone_controller import drone_controller
from flask_cors import CORS
import threading
import time
import requests
import firebase_admin
from firebase_admin import credentials, firestore_async


app = Flask(__name__)
app.secret_key = "your_secret_key_here" 
CORS(app)
drone_in_flight = False
message = ''
#drone_controller = DroneController()

# Use a service account.
cred = credentials.Certificate('cps-dragonfly-96f4336104bf.json')
firebase_app = firebase_admin.initialize_app(cred)
db = firestore_async.client()

host = "127.0.0.1"
user = "root"
password = "qwe123qwe"
database = "dragonfly"


@app.route('/battery', methods=['GET'])
def get_battery_status():
    battery_status = drone_controller.get_battery()
    return jsonify(battery_status)

@app.route('/takeoff', methods=['POST'])
def takeoff():
    drone_controller.takeoff()
    global drone_in_flight  # Use the global keyword
    message = 'Drone is taking off!'
    drone_in_flight = True
    print(drone_in_flight)
    return jsonify(message)

@app.route('/land', methods=['POST'])
def land():
    drone_controller.landing()
    message = "Drone is landing!"
    global drone_in_flight  # Use the global keyword
    drone_in_flight = False
    return jsonify(message)

@app.route('/read_scan_code')
def read_scan_code():
    detected_scan_code = drone_controller.drone_ar.get_latest_barcode()
    app.logger.debug("Detected barcode: %s", detected_scan_code)  # Log the value

    return detected_scan_code

@app.route('/reset_scan_code', methods=['POST'])
def reset_scan_code():
    drone_controller.drone_ar.code_latest = ''
    return jsonify({'message': 'Scan code is reset'}), 200


@app.route('/video_feed')
def video_feed():
    return Response(drone_controller.video_stream_generator(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/send_command', methods=['POST'])
def send_command():
    global drone_in_flight
    print(drone_in_flight)

    data = request.get_json()
    print("Received data:", data)

    command = data.get('command')
    print("Received data:",command)

    
    if drone_in_flight:
        if command in ['move_up', 'move_down', 'move_left', 'move_right', 'move_forward', 'move_backward', 'rotate_left', 'rotate_right']:
            # Process drone movement commands
            # Your existing command handling logic here
            if command == 'move_up':
                drone_controller.drone.move_up(25)
            elif command == 'move_down':
                drone_controller.drone.move_down(25)
            elif command == 'move_left':
                drone_controller.drone.move_left(25)
            elif command == 'move_right':
                drone_controller.drone.move_right(25)
            elif command == 'move_forward':
                drone_controller.drone.move_forward(25)
            elif command == 'move_backward':
                drone_controller.drone.move_backward(25)
            elif command == 'rotate_left':
                drone_controller.drone.rotate_ccw(25)
            elif command == 'rotate_right':
                drone_controller.drone.rotate_cw(25)
            return jsonify({'message': 'Command executed successfully'}), 200
        else:
            return jsonify({'message': 'Invalid command'}), 400
    else:
        return jsonify({'message': 'Drone is not in flight'}), 400
        
@app.route('/automated', methods=['POST'])
def automated_commands():
    global drone_in_flight

    if drone_in_flight:
        return jsonify({'message': 'Drone is already in flight'}), 400

    # commands = request.form.get('commands')
 
    
    # if not commands:
    #     return jsonify({'message': 'No commands provided'}), 400

    # commandArray = commands.split("\n")
    commandArray = request.get_json()
    print(commandArray)
    drone_controller.takeoff()
    drone_in_flight = True
    # flash("Start mission!", "info")
    time.sleep(10)

    for command in commandArray:
        parts = command.split()
        if len(parts) == 2:
            direction, distance = parts
            if direction in ['up', 'down', 'left', 'right', 'forward', 'backward']:
                drone_controller.drone.move(direction, int(distance))
                time.sleep(5)
                # print(f'Direction: {direction}, Value: {distance}')
            elif direction == 'rotate_ccw':
                drone_controller.drone.rotate_ccw(int(distance))
                time.sleep(5)
            elif direction == 'rotate_cw':
                drone_controller.drone.rotate_cw(int(distance))
                time.sleep(5)
            else:
                return jsonify({'message': f'Invalid direction: {direction}'}), 400
        else:
            return jsonify({'message': f'Invalid command format: {command}'}), 400
    time.sleep(5)
    drone_controller.landing()
    drone_in_flight = False
    return jsonify({'message': 'Automated successfully'}), 200

@app.route('/test', methods=['GET'])
def test():
    data = {"message":"Drone is ON TEST!"}
    return jsonify(data)

##################################################################################################
###################Still under development########################################################
def check_internet_connection():
    try:
        response = requests.get("http://www.google.com", timeout=5)
        response.raise_for_status()
        print('there is internet connection')
        return True
    except requests.RequestException:
        return False

def upload_to_firebase(qr_codes, flight_path):
    qr_codes_ref = db.collection('inventory_checks')

    # Add a document for the inventory check
    inventory_check_data = {
        "Scanned_qr_codes": qr_codes,
        "Flight_path": flight_path
    }

    # Add the inventory check data to Firestore
    qr_codes_ref.add(inventory_check_data)


def save_to_local_backup(qr_codes):
    # Save the QR code data to a local file
    with open("local_backup.txt", "a") as file:
        file.write(qr_codes + "\n")

@app.route('/upload_result', methods=['POST'])
def upload_scanned_result():
    if not check_internet_connection():
        try:
            qr_code_data = request.json.get('qr_code_data')
            save_to_local_backup(qr_code_data)
            return jsonify({"message": "QR code saved to local backup"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    try:
        # if Internet connection is available, try to upload to Firebase
        qr_code_data = request.json.get('qr_code_data')
        flight_path_data = request.json.get('flight_path_data')
        upload_to_firebase(qr_code_data,flight_path_data)

        return jsonify({"message": "QR code uploaded successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Function to execute SELECT queries
def get_command(scan_code):
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )

        cursor = connection.cursor()

        # Query to retrieve movement instruction based on scan code
        query = "SELECT command FROM items WHERE item_code = %s"
        cursor.execute(query, (scan_code,))

        result = cursor.fetchone()

        cursor.close()
        connection.close()
        command = str(result[0])
        return command

    except mysql.connector.Error as err:
        # Handle database errors
        print(f"Database error: {err}")
        return None

@app.route('/qrcode_control', methods=['POST'])
def qrcode_control():
    # drone_controller.takeoff()
    # time.sleep(3)
    try:
        latest_scan_code = drone_controller.drone_ar.get_latest_barcode()
       
        # if len(latest_scan_code)>0:
        #     detected = True
        # else:
        #     detected = False        
        while(len(latest_scan_code)>0):
             # Call the execute_select_query function
            command = get_command(latest_scan_code)
            if command:
                if command != 'land':
                    print(command)
                    print(latest_scan_code)
                    time.sleep(5)
                else:
                    print(command)
                    drone_controller.drone_ar.code_latest = ''
                    break
            else: 
                #landing
                return jsonify(f"This QR has no {command}")
            
            latest_scan_code = drone_controller.drone_ar.get_latest_barcode()

        return jsonify("QR Guilded mode")
    except Exception as e:
        # Handle other exceptions
        print(f"Error: {e}")
        return jsonify("Internal Server Error")
    
if __name__ == '__main__':
    app.run(debug=True)
 
