# feeder test
# only works if serial data is there



import os, sys
from random import shuffle, choice
from glob import glob


import serial
import csv
import time
import threading

arduino_port = "COM3"  # Serial port of Arduino for IR beams; ADJUST for the computer used
baud = 9600  # Arduino Uno runs at 9600 baud


ser = serial.Serial(arduino_port, baud)  #COM Port - set up serial read
ser.reset_input_buffer() #clears buffer before starting

print("Connected to Arduino port: " + arduino_port)
#log data!#################################################################

# function to get the time
def get_time():
	t = time.gmtime()
	s = str(t.tm_hour) + ':' + str(t.tm_min) + ':' + str(t.tm_sec)
	return s
 
    

# function to get the date
def get_date():
	t = time.gmtime()
	s = str(t.tm_year) + '/' + str(t.tm_mon) + '/' + str(t.tm_mday)
	return s



############################################################################
#################### variables #############################################
############################################################################

data_exit_flag = False
data = ""

reward_status = 0
timeout_status = 0
detection_t = 0

# Global variable to control thread pause/resume
pause_threads = False




def send_message(message):      #to activate the feeder later
    ser.write(message.encode())




def read_data():  # new thread to ensure data is read
    prev_data = "nix"
    global pause_threads
    global data
    while not data_exit_flag:
            
        while pause_threads:         #handles global variable for a timeout
                time.sleep(1)
                print("read_data() thread paused")
                
        data = ser.readline().decode('utf-8').strip()
        time.sleep(0.1)
        prev_data = data

#one liner doesn't work (cannot join)
#data_thread = threading.Thread(target=read_data, daemon = True).start()
data_thread = threading.Thread(target=read_data)
data_thread.daemon = True
data_thread.start()


##########################################################################
##### read data - main loop ##############################################
##########################################################################

try:
        #ser.timeout = 0.25
        reward_timer = time.time()
        #data = ser.readline().decode('utf-8').strip()
        while not data_exit_flag:
                
                print(data)
                    
                time.sleep(0.05)

                print("activate Feeder")
                send_message("motor_on") 
                reward_status = 1
                           
                print("Timeout to eat")
                time.sleep(0.1)
                print ("continued")                       
                                        
                time.sleep(0.05)

                        
except KeyboardInterrupt:
        data_exit_flag = True
        print("\nData collection interrupted by user. Saving data to CSV...")
        interruption_time = get_date() + ' - ' + get_time() + '\n'
        print("\nData collection interrupted by user. Sounds stop at:", interruption_time)
        






data_thread.join()

ser.close()






