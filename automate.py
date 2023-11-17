import tello
import time
drone = tello.Tello('', 8889)

drone.takeoff()
time.sleep(5)
drone.move_up(30)
time.sleep(5)
drone.move_forward(30)
time.sleep(5)
drone.rotate_ccw(50)
time.sleep(5)
drone.move_forward(30)
time.sleep(5)
drone.land()