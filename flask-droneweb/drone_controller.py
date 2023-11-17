import sys
sys.path.append('/home/dragonfly/Documents/GitHub/DragonFly/Development-Code/DJI Tello/New UI (Python 3.6.9)')

import logging
import tello 
import cv2 
from drone_ar_flight import Drone_AR_Flight
logging.basicConfig(level=logging.DEBUG)

class DroneController:
    def __init__(self):
        self.drone = None
        self.drone_ar = Drone_AR_Flight()

    def initialize_drone(self):
        if self.drone is None:
            self.drone = tello.Tello('', 8889)

    def takeoff(self):
        self.initialize_drone()
        self.drone.takeoff()

    def landing(self):
        self.initialize_drone()
        self.drone.land()

    def get_battery(self):
        self.initialize_drone()
        battery_status = self.drone.get_battery()
        return f'{battery_status}%'

    def video_stream_generator(self):
        self.initialize_drone()
        while True:
            frame_h264 = self.drone.read_video_frame()
            if frame_h264 is not None:
                # logging.debug('Sending video frame')
                # print("Frame dimensions:", frame_h264.shape)
                # print("Frame data type:", frame_h264.dtype)

                #decode h264 frames
                #frame_bgr = cv2.cvtColor(frame_h264, cv2.COLOR_YUV2BGR_I420)
                #convert bgr frames to JPEG format
                self.drone_ar.renew_frame(self.drone.read_video_frame(), 
                                          self.drone_ar.frame_no, 
                                          0, 
                                          'MANUAL', 
                                          0)
                _, frame_jpeg = cv2.imencode(".jpg", frame_h264)
                headers = (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n')
                yield headers + frame_jpeg.tobytes() + b'\r\n'
        
    # def read_scan_code(self):
    #     self.drone_ar.renew_frame(self.drone_ar.frame, 
    #                               self.drone_ar.frame_no, 
    #                               0, 
    #                               'MANUAL', 
    #                               0)
    #     # self.drone_ar._detect2()
    #     self.drone_ar._try_read_barcode()
    #     return self.drone_ar.get_latest_barcode()

    def close(self):
        if self.drone is not None:
            self.drone.close()

# Create an instance of DroneController
drone_controller = DroneController()