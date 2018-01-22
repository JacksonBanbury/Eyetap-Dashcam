#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created by Jackson Banbury and the OpenEyetap team at the University of Toronto

www.openeyetap.org

YouTube upload implementation thanks to github.com/tokland

To run the script at startup, you can add it to ~/.bashrc with the following line:
python /path/to/dashcam.py

"""
import io
import os
import time
import picamera
import picamera.array
import pyaudio,wave,sys
import datetime as dt
import RPi.GPIO as GPIO


wd = '/home/pi/Documents/dashcam'

# Set audio as True or False here
audiostate = False

# Audio-related paramters
chunk = 8192 #size of chunk for audio
audiorate = 44100 #rate at which audio is recorded. try adjusting this if audio is out of sync
audioframes = []

# Time before and after the button press, in seconds
timebefore = 90
timeafter = 30
timetotal = timebefore + timeafter

cnt = 0

# Recording resolution - note higher resolution means larger files! 
resolution='VGA'
reswidth = 640
resheight = 480
framerate = 24 # framerate - note higher means larger files!
fontSize = 60 # font size of the on-screen notification

# Change GPIO pin for button here!
bpin = 18

# Initializing GPIO for button press
GPIO.setmode(GPIO.BCM)
GPIO.setup(bpin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Timestamp variable initalizer
timestampbuffer = 0.0

#Button press
def ButtonPress():
    input_state = GPIO.input(bpin)
    return not(input_state)

def CurrentTime():
    return('%s')%(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

def sec():
    sec.var = dt.datetime.now().strftime('%S')
    return sec.var

sec.var=0 # initializes the sec variable, to be used later

def Timestamp():
    if (dt.datetime.now().strftime('%S') != sec.var): # accesses the second value from the last time sec() was called
        # updates the annotation on the video if a second has passed
        camera.annotate_text_size = fontSize
        camera.annotate_background = picamera.Color('black')
        camera.annotate_text = CurrentTime()
        sec() # calls the second function so that it can update its current second value

def WriteVideo(stream, filename):
    print("Writing video to %s"%(filename))
    with stream.lock:
        # Find the first header frame in the video
        for frame in stream.frames:
            if frame.header:
                stream.seek(frame.position)
                break
        # Write the rest of the stream to disk
        with io.open(filename, 'wb') as output:
            output.write(stream.read())
    print("Writing successful")


# Main

with picamera.PiCamera(resolution=resolution, framerate=framerate) as camera:
    camera.rotation = 90 # depends on the orientation of the pi camera
    camera.start_preview()
    stream = picamera.PiCameraCircularIO(camera, seconds=timetotal, bitrate=1000000)
    camera.start_recording(stream, format='h264', bitrate=1000000, quality=22)	
        
    try:
        while True:
            Timestamp() # Shows timestamp on top of video
            if ButtonPress():
                print("Button Pressed") # For debugging purposes
                camera.annotate_text =   "%s   Button Pressed!" %(CurrentTime())
                # start audio recording if selected
                if audiostate:
                    audio = pyaudio.PyAudio()
                    audiostream = audio.open(format=pyaudio.paInt16,
                            channels = 1,
                            rate = audiorate,
                            input = True,
                            input_device_index = 0,
                            frames_per_buffer = chunk)
                    for i in range(0, int(audiorate / chunk * timeafter)):
                            audiodata = audiostream.read(chunk)
                            audioframes.append(audiodata)
                            
                camera.wait_recording(timeafter) # continues to record after the button is pressed

                if audiostate:
                    audiostream.stop_stream()
                    audiostream.close()
                    audio.terminate()

                    # Create Wave file for audio
                    wavefile = wave.open('Audio.wav', 'wb')
                    wavefile.setnchannels(1)
                    wavefile.setsamplewidth(audio.get_sample_size(pyaudio.paInt16))
                    wavefile.setframerate(audiorate)
                    wavefile.writeframes(b''.join(audioframes))
                    wavefile.close()                  
               
                # Stop recording to allow pi to write to disk (otherwise can freeze)
                #camera.stop_recording()

                # Writing video to disk
                #vidname = 'video_on_%s.h264'%(CurrentTime())
                vidname = 'dashcamvid.h264'
		WriteVideo(stream, vidname)

                #Merge Audio/Video file into an MKV
                if audiostate:
                    merge = 'ffmpeg -y -itsoffset timebefore  -i Audio.wav -r 30 -i %s -filter:a aresample=async=1 -c:a flac -c:v copy dashcam.mkv'%vidname
                
             
                #Upload to YouTube - Ensure your YouTube credentials are located at the directories below (or specify them here):
                os.system('youtube-upload --title="Dashcam Video from the EyeTap!" --description="Video recorded on EyeTap - visit OpenEyetap.org" --tags="wearable,dashcam,eyetap,technology" --client-secrets=/home/pi/Documents/dashcam/client_secrets.json --credentials-file=/home/pi/.youtube-upload-credentials.json %s'%vidname)
        

    except ValueError as verr:
        print verr
