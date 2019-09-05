#! /home/pi/.virtualenvs/cv/bin/python3.7
import os
from picamera import PiCamera
from picamera.array import PiRGBArray
import imutils
import cv2

import datetime
import multiprocessing
import time
from ctypes import c_bool

filename = "last_recorded_time.txt"  #Change this later please to include relevant details, and path of network
write_time = multiprocessing.Value(c_bool, True) 
net_drive_path = "TestDrive/"
fps_document = "fps.txt" #Change later please to include network path
resolution = (640, 480)
framerate = 10
fid = open(fps_document, mode = 'w', encoding = 'utf-8')
fid.write(str(framerate))
fid.close()

def motion_detection():
    with PiCamera() as cv_camera:
        cv_camera.resolution = resolution
        cv_camera.framerate = framerate
        min_area = 5000
        rawCapture = PiRGBArray(cv_camera, size=(640,480))
        avg = None
        delta_thresh = 5
        motion_detected = False
        time.sleep(0.1)
        frame_count = 0
        motion_counter = 0
        for f in cv_camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            frame = f.array
            frame_count = frame_count + 1
            frame = imutils.resize(frame, width=500)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            if avg is None:
                avg = gray.copy().astype("float")
                rawCapture.truncate(0)
                continue
            cv2.accumulateWeighted(gray, avg, 0.5)
            frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
            thresh = cv2.threshold(frameDelta, delta_thresh, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)
            for c in cnts:
                if cv2.contourArea(c) < min_area:
                    continue

                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                if (frame_count >= 6):
                    print("motion detected")
                    motion_counter += 1
                dt_now = datetime.datetime.now()
                motion_frame_name = str(motion_counter) + "_" + str(dt_now.month) + "-" + str(dt_now.day) + "-" + str(dt_now.year) + " " + str(dt_now.hour) + ":" + str(dt_now.minute) + ":" + str(dt_now.second)
                cv2.imwrite(motion_frame_name + ".jpg", frame)
                cv2.imwrite(motion_frame_name + "_thresh" + ".jpg", thresh)
                if (motion_counter >= 6):
                    motion_detected = True
            cv2.imshow("Frame", frame)
            cv2.imshow("Thresh", thresh)
            cv2.waitKey(5)

            if (motion_detected == True):
                break
            if (frame_count >= cv_camera.framerate * 2*60*60):
                break
            rawCapture.truncate(0)
        cv2.destroyAllWindows()
    #del cv_camera
    return motion_detected

def take_video():
    with PiCamera() as camera:
        #camera = PiCamera()
        camera.resolution = resolution
        camera.framerate = framerate
        num_vids = 30                         #Sets how many videos per day
        vidlength =  30                             #Sets time needed for each video
        for x in range(num_vids):
            timenow = datetime.datetime.now()       #Gets time now
            filename = str(str(timenow.month) + "-" + str(timenow.day) + "-" + str(timenow.year) + " " + str(timenow.hour) + str(':') + str(timenow.minute) + str(':') + str(timenow.second))                # Sets time now as the filename
            filelocation = filename   #Sets file location
            camera.start_preview()
            camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.start_recording(filelocation + str('.h264'))
            reference = datetime.datetime.now()
            while ((datetime.datetime.now() - reference).seconds < vidlength):
                camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.wait_recording(1)
            camera.stop_recording()
            camera.stop_preview()
        time.sleep(0.5)
    #    del camera


def process_time(write_time):
    while (write_time.value == True):
        try:
            fid = open(filename, mode = 'r', encoding = 'utf-8')
            previous_time = fid.readline()
        finally:
            fid.close()
        try:
            fid = open(filename, mode = 'w', encoding = 'utf-8')
            timenow = datetime.datetime.now()
            timestring = "Time: " + str(timenow.hour) + ":" + str(timenow.minute) + ":" + str(timenow.second) + "  Date: " + str(timenow.month) + "/" + str(timenow.day) + "/" + str(timenow.year)
            fid.write(timestring)
        finally:
            fid.close()
        for i in range(120):
            if (write_time.value == True):
                time.sleep(1)
            else:
                break

if __name__ == "__main__":
    while True:
        try:
            timewrite = multiprocessing.Process(target=process_time, args=(write_time,))
            write_time.value = True
            timewrite.start()
            time.sleep(1)
            motion_detected = motion_detection()
            if (motion_detected == True):
                take_video()
            write_time.value = False
            time.sleep(1)
            timewrite.join()
        except KeyboardInterrupt:
            camera.stop_recording()
            camera.stop_preview()
            write_time.value = False
            timewrite.join()