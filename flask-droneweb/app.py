
from flask import Flask, render_template, request, flash, redirect, url_for,Response,jsonify
from drone_controller import drone_controller
import threading


app = Flask(__name__)
app.secret_key = "your_secret_key_here" 
drone_in_flight = False
#drone_controller = DroneController()

@app.route('/')
def index():
    battery_status = drone_controller.get_battery()
    return render_template('index.html',battery_status=battery_status)


@app.route('/takeoff', methods=['POST'])
def takeoff():
    drone_controller.takeoff()
    flash("Drone is taking off!", "info")
    global drone_in_flight  # Use the global keyword
    drone_in_flight = True
    print(drone_in_flight)
    return redirect(url_for('index'))
    #return "Drone is taking off!"

@app.route('/land', methods=['POST'])
def land():
    drone_controller.landing()
    flash("Drone is landing!", "info")
    global drone_in_flight  # Use the global keyword
    drone_in_flight = False
    return redirect(url_for('index'))
    #return "Drone is landing!"

@app.route('/read_scan_code')
def read_scan_code():
    #scan_code_detected = drone_controller.read_scan_code()
    read_the_code = drone_controller.drone_ar.renew_frame(drone_controller.drone.read_video_frame(), 
                                                          drone_controller.drone_ar.frame_no, 
                                                          0, 
                                                          'MANUAL', 
                                                          0)
    detected_scan_code = drone_controller.drone_ar.get_latest_barcode()
    app.logger.debug("Detected barcode: %s", detected_scan_code)  # Log the value
    return detected_scan_code

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
                drone_controller.drone.move_up(20)
            elif command == 'move_down':
                drone_controller.drone.move_down(20)
            elif command == 'move_left':
                drone_controller.drone.move_left(20)
            elif command == 'move_right':
                drone_controller.drone.move_right(20)
            elif command == 'move_forward':
                drone_controller.drone.move_forward(20)
            elif command == 'move_backward':
                drone_controller.drone.move_backward(20)
            return jsonify({'message': 'Command executed successfully'}), 200
        else:
            return jsonify({'message': 'Invalid command'}), 400
    else:
        return jsonify({'message': 'Drone is not in flight'}), 400

if __name__ == '__main__':
    app.run(debug=True)
