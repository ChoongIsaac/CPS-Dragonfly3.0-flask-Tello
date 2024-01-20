from flask import Flask, render_template, request, flash, redirect, url_for, Response, jsonify
import mysql.connector
from drone_connection import drone_connection
from flask_cors import CORS
import threading
import time
import requests
import firebase_admin
from firebase_admin import credentials, firestore_async

class DroneApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "your_secret_key_here"
        CORS(self.app)
        self.drone_in_flight = False
        self.message = ''
        self.flight_path = []

        self.host = "127.0.0.1"
        self.user = "root"
        self.password = "qwe123qwe"
        self.database = "dragonfly"

        self.drone_connection= drone_connection
        self.drone_connection.mode = 'manual'

        self.setup_routes()
    #function to setup API Route
    def setup_routes(self):
        self.app.route('/battery', methods=['GET'])(self.get_battery_status)
        self.app.route('/reset_flight_path', methods=['POST'])(self.reset_flight_path)
        self.app.route('/takeoff', methods=['POST'])(self.takeoff)
        self.app.route('/land', methods=['POST'])(self.land)
        self.app.route('/read_scan_code')(self.read_scan_code)
        self.app.route('/reset_scan_code', methods=['POST'])(self.reset_scan_code)
        self.app.route('/video_feed')(self.video_feed)
        self.app.route('/send_command', methods=['POST'])(self.send_command)
        self.app.route('/automated', methods=['POST'])(self.automated_commands)
        self.app.route('/qrcode_navigate', methods=['POST'])(self.qrcode_navigate)
        self.app.route('/flight_path', methods=['GET'])(self.get_flight_path)
        self.app.route('/reset_flight_path', methods=['POST'])(self.reset_flight_path)

    def run(self):
        self.app.run(debug=True)

    def get_battery_status(self):
        battery_status = self.drone_connection.get_battery()
        return jsonify(battery_status)

    def reset_flight_path(self):
        self.flight_path = []
        return jsonify({'message': 'flight path is reset'}), 200

    def takeoff(self):
        self.drone_connection.takeoff()
        self.drone_in_flight = True
        self.flight_path.append("takeoff")
        print(self.drone_in_flight)
        return jsonify("Drone is taking off!")

    def land(self):
        self.drone_connection.landing()
        self.drone_in_flight = False
        self.flight_path.append("land")
        return jsonify("Drone is landing!")

    def read_scan_code(self):
        detected_scan_code = self.drone_connection.drone_ar.get_latest_barcode()
        self.app.logger.debug("Detected barcode: %s", detected_scan_code)  # Log the value
        return detected_scan_code

    def reset_scan_code(self):
        self.drone_connection.drone_ar.code_latest = ''
        return jsonify({'message': 'Scan code is reset'}), 200

    def video_feed(self):
        return Response(self.drone_connection.video_stream_generator(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    #function to send command to tello in manual mode
    def send_command(self):
        data = request.get_json()
        command = data.get('command')

        if self.drone_in_flight:
            if command in ['move_up', 'move_down', 'move_left', 'move_right', 'move_forward', 'move_backward',
                           'rotate_left', 'rotate_right']:
                if command == 'move_up':
                    self.drone_connection.drone.move_up(40)
                    self.flight_path.append("up 40")
                elif command == 'move_down':
                    self.drone_connection.drone.move_down(40)
                    self.flight_path.append("down 40")
                elif command == 'move_left':
                    self.drone_connection.drone.move_left(40)
                    self.flight_path.append("left 40")
                elif command == 'move_right':
                    self.drone_connection.drone.move_right(40)
                    self.flight_path.append("right 40")
                elif command == 'move_forward':
                    self.drone_connection.drone.move_forward(40)
                    self.flight_path.append("forward 40")
                elif command == 'move_backward':
                    self.drone_connection.drone.move_backward(40)
                    self.flight_path.append("backward 40")
                elif command == 'rotate_left':
                    self.drone_connection.drone.rotate_ccw(40)
                    self.flight_path.append("rotate_left 40")
                elif command == 'rotate_right':
                    self.drone_connection.drone.rotate_cw(40)
                    self.flight_path.append("rotate_right 40")
                return jsonify({'message': 'Command executed successfully'}), 200
            else:
                return jsonify({'message': 'Invalid command'}), 400
        else:
            return jsonify({'message': 'Drone is not in flight'}), 400

    def automated_commands(self):
        if self.drone_in_flight:
            return jsonify({'message': 'Drone is already in flight'}), 400

        commandArray = request.get_json()
        print(commandArray)
        self.drone_connection.takeoff()
        self.flight_path.append("takeoff")
        self.drone_in_flight = True
        time.sleep(5)

        for command in commandArray:
            parts = command.split()
            if len(parts) == 2:
                direction, distance = parts
                if direction in ['up', 'down', 'left', 'right', 'forward', 'backward']:
                    self.drone_connection.drone.move(direction, int(distance))
                    self.flight_path.append(parts)
                    time.sleep(5)
                elif direction == 'rotate_ccw':
                    self.drone_connection.drone.rotate_ccw(int(distance))
                    self.flight_path.append(f"rotate_left {distance}")
                elif direction == 'rotate_cw':
                    self.drone_connection.drone.rotate_cw(int(distance))
                    self.flight_path.append(f"rotate_right {distance}")
                
        time.sleep(5)
        self.drone_connection.landing()
        self.flight_path.append("land")
        self.drone_in_flight = False
        return jsonify({'message': 'Automated successfully'}), 200

    def create_mysql_connection(self):
        try:
            # Establish a connection to the MySQL server
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )

            print("Database connection established.")
            return connection

        except mysql.connector.Error as err:
            # Handle database connection errors
            print(f"Database connection error: {err}")
            return None
        
    def get_command(self,scan_code):
        try:
            connection = self.create_mysql_connection()

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

    def qrcode_navigate(self):
        try:
            self.drone_connection.mode = 'OR_Navigated'
            self.drone_connection.takeoff()
            self.flight_path.append("takeoff")
            #must execute this to have time interval
            time.sleep(5)
            prev_scan_code = ''
            latest_scan_code = self.drone_connection.drone_ar.get_latest_barcode()

            while True:
                #check latest scan code is the same with prev
                if latest_scan_code == prev_scan_code:
                    self.drone_connection.landing()
                    break
                prev_scan_code = latest_scan_code
                if len(latest_scan_code) > 0:
                    command = self.get_command(latest_scan_code)
                    time.sleep(3)
                    parts = command.split()

                if command:
                    if command != 'land':
                        print(command)
                        if len(parts) == 2:
                            direction, distance = parts
                            if direction in ['up', 'down', 'left', 'right', 'forward', 'backward']:
                                self.drone_connection.drone.move(direction, int(distance))
                                self.flight_path.append(parts)
                                time.sleep(5)
                            elif direction == 'rotate_ccw':
                                self.drone_connection.drone.rotate_ccw(int(distance))
                                self.flight_path.append(f"rotate_left {distance}")
                            elif direction == 'rotate_cw':
                                self.drone_connection.drone.rotate_cw(int(distance))
                                self.flight_path.append(f"rotate_right {distance}")
                        else:
                            return jsonify({'message': f'Invalid command format: {command}'}), 400
                        print(latest_scan_code)
                    else:
                        print(command)
                        self.drone_connection.landing()
                        self.flight_path.append("land")
                        self.drone_connection.drone_ar.code_latest = ''
                        self.drone_connection.mode = 'manual'
                        break
                else:
                    self.drone_connection.landing()
                    self.flight_path.append("land")
                    self.drone_connection.drone_ar.code_latest = ''
                    return jsonify(f"This QR has no {command}")

                latest_scan_code = self.drone_connection.drone_ar.get_latest_barcode()

            return jsonify("QR Navigation mode")
        except Exception as e:
            print(f"Error: {e}")
            return jsonify("Internal Server Error")

    def get_flight_path(self):
        return jsonify(self.flight_path)
    
    def reset_flight_path(self):
        self.flight_path = [];
        return jsonify({'message': 'flight path is reset'}), 200

if __name__ == '__main__':
    drone_app = DroneApp()
    drone_app.run()
