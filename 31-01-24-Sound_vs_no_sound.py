'''

Connect IR beams, RFID and feeder for a sound vs. no sound phase in an operant task


22-01-23: NEW IDEA by Pui Pui: start playing sounds when a bird is there -> recognized by RFID tag
+ maybe improve timeout.. stop sounds and maybe just stop everything until IR beams are not disrupted anymore? -> DONE

Reaction types: HIT, MISS

Problems: IR Beams can stay broken forever and bird is rewarded all the time -> DONE
Now also sounds stop when 
      
'''
##########################################################################
##### import things ######################################################
##########################################################################

import os
from random import shuffle, choice
from glob import glob


## Imports for IR beams ##################################################

import serial
import csv
import time

## imports for sound

import winsound
import threading
import random

import config_operant as c

folder_path_sound = c.folder_path_sound # folder in which each consonant sound lasts 0.5 seconds


sound_files = os.listdir(folder_path_sound)

Sound_data = [] 


random.shuffle(sound_files) # shift in a loop and shuffle new every x sounds; config file for different conditions


arduino_port = c.arduino_port # Serial port of Arduino for IR beams; ADJUST 
baud = 9600  # Arduino Uno runs at 9600 baud
fileName = c.fileName_Phase2 #"Sound_noSound.csv"  # Name of the CSV file generated

ser = serial.Serial(arduino_port, baud)  #COM Port - set up serial read
ser.reset_input_buffer() #clears buffer before starting

print("Connected to Arduino port: " + arduino_port)
time.sleep(1)



############################################################################
#################### variables #############################################
############################################################################

playing = False
sound_exit_flag = False
data_exit_flag = False
sound_playing = False
endsound_t = 0
reward_status = 0
timeout_status = 0
keyboard_interrupt = False
identity = ""   # Initialize identity string variable
IR_bird_status = ""  # Initialize string variable to recognize if IR beam is broken or not
bird_on_perch = False # variable to handle RFID data -> maybe has to be changed later
detection_t = 0
bird_on_perch = False
previous_ID = None
current_sound = None
pause = False

sounds_in_folder = 24 ############ CHANGE HERE dependng on the number of files in the folder
sound_counter = 0

data = ""

last_row = ["11:11:11", "3BXXXXXX", "X", "X", "X", "X"]




############################################################################
#################### time functions ########################################
############################################################################


# function to get the time
def get_time():
	t = time.localtime()
	s = str(t.tm_hour) + ':' + str(t.tm_min) + ':' + str(t.tm_sec)
	return s
 

# function to get the date
def get_date():
	t = time.localtime()
	s = str(t.tm_year) + '/' + str(t.tm_mon) + '/' + str(t.tm_mday)
	return s

##########################################################################
##### set up data log ####################################################
##########################################################################

with open(fileName, 'a', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([])
    writer.writerow(["Start time: ", get_date(), ' - ' + get_time()])
    writer.writerow(["Timestamp", "Identity", "Bird status/IR", "Reward status", "Sound", "Reaction type "])
    writer.writerow([])

print("Appended file: state, header, start time")

print_labels = False


recent_responses = [] # store bird status in the list of recent responses after a sound

##########################################################################
##### define functions ###################################################
##########################################################################

def play_sound(sound_files, folder_path_sound):        # sounds will keep playing as long as bird_on_perch is true or data starts with "3B".. currently reset after  
    sound_list = []
    global sound_playing, sound_exit_flag, endsound_t
    global sound_counter
    global sounds_in_folder
    global current_sound
    global pause

    while not data_exit_flag:

            #while bird_on_perch:
            while data.startswith("3B") or bird_on_perch: 
                    for sound in sound_files:
                        while pause:
                             time.sleep(1)
                             print("Sound pause")

                        print(sound)
                        sound_list.append(sound.strip())
                        current_sound = sound
                        sound_playing = True
                        winsound.PlaySound(os.path.join(folder_path_sound, sound), winsound.SND_FILENAME)
                        endsound_t = time.time()
                        sound_playing = True
                        time.sleep(5) # duration between sounds in sec 
                        sound_playing = False
                        sound_counter = sound_counter + 1   # important to shuffle sounds new after each sound in the folder is shuffled
                        #print("sound_counter ", sound_counter)

                        if sound_counter == sounds_in_folder and not sound_exit_flag:
                                random.shuffle(sound_files)
                                sound_counter = 0 # reset the counter
                                print("shuffled new")

                        if sound_exit_flag: #to exit the for loop
                                random.shuffle(sound_files)   # to make sure the sounds are shuffled new -> no repeated sounds
                                break   # -> exit the for loop
                        
                    if sound_exit_flag: 
                        break  # -> exit the while loop


def send_message(message):      #to activate the feeder
    ser.write(message.encode())

def read_data():  # new thread to ensure data is read
    prev_data = "nix"
    global data
    while not data_exit_flag:
        data = ser.readline().decode('utf-8').strip()
        time.sleep(0.1)
        prev_data = data
        
def is_sound_playing():
    return sound_playing #flag set in the definition of play_sound()

sound_thread = threading.Thread(target=play_sound, args=(sound_files, folder_path_sound))   # start the sound thread
sound_thread.daemon = True # to let it run in the background
sound_thread.start()

data_thread = threading.Thread(target=read_data)  # start the data thread
data_thread.daemon = True
data_thread.start()


try:
    
    ser.timeout = 0.1
    while not data_exit_flag:
        if data:
            print(data)
            current_t = time.time()
            #print("Current time: ", current_t)
            time_elapsed = current_t - endsound_t #endsound_t is taken above in the play sound loop
            #print("Time elapsed: ", time_elapsed)
            timestamp = get_time()  

            if data.startswith("3B"):
                    bird_on_perch = True
                    identity = data
                    if identity != previous_ID:
                            #print ("Bird ID:  ", data)
                            previous_ID = data
                            log_prev_ID = data
                            detection_t = time.time()
                            sound_exit_flag = False
                            Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, ""]) # to see how long a bird stayed later
                            time.sleep(0.01)

            elif data == "Bird" and sound_playing == False and time_elapsed <= 2 and reward_status == 0: # CORRECT RESPONSE: sound is over but was presented only two seconds or less ago -> HIT
                print("correct response - activate feeder to get a reward")#sound is over but was presented only two seconds or less ago
                send_message("motor_on") #command to activate feeder through the arduino
                data = IR_bird_status
                identity = previous_ID
                bird_on_perch = True
                reward_status = 1
                Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "HIT"])
                time.sleep(3)

                
            elif data == "Bird" and sound_playing == True and reward_status == 0:  # too early response, still rewarded.. sound duration only 0.5 sec -> HIT
                print("too early, still rewarded - activate feeder to get a reward")
                send_message("motor_on") #command to activate feeder through the arduino
                reward_status = 1
                #sound_exit_flag = True
                data = IR_bird_status
                identity = previous_ID
                bird_on_perch = True 
                Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "HIT"])
                time.sleep(3) 
                                        
                #previously this condition was WRONG: Timeout if IR beam is broken too late  -> NOISE -> WRONG       
                #now also MISS -> keep sounds playing - no noise
                    
            elif data == "Bird" and sound_playing == False and time_elapsed >= 2: #response without sound -> MISS
                print("no reward - wrong response")
                reward_status = 0
                bird_on_perch = True
                identity = previous_ID
                
                IR_bird_status = "Bird" #will not be logged otherwise
                Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "MISS"]) # previously was saying WRONG here


            elif data == "noBird" and time_elapsed >= 2 and endsound_t != 0: #and reward_status == 1:  #no response where there should be a response -> Timeout -> MISS
                print("no reward - no response")
                reward_status = 0

                #time.sleep(5)  # rethink maybe
            
                IR_bird_status = "noBird" #will not be logged otherwise
                Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "MISS"])

                endsound_t = 0
                bird_on_perch = False #?????????????????
                
                #sound_exit_flag = True
                

            elif reward_status == 1:        #only happens when bird has been rewarded by breaking IR beam
                while data != "noBird": #break the loop when bird leaves the IR sensor
                        print("paused until IR beams are free again")
                        time.sleep(1)
                        sound_exit_flag = True 
                        pause = True

                                
                # Reset variables
                reward_status = 0       #reward status is still 1 because this bird just got rewarded and it has to be logged
                previous_ID = None      #reset ID that the same bird can be rewarded again
                bird_on_perch = False # correct?
                pause = False

            time.sleep(0.1)

except KeyboardInterrupt:
    keyboard_interrupt = True
    print("\nData collection interrupted by user.")
    data_exit_flag = True
    sound_exit_flag = True
    sound_playing = False
    bird_on_perch = False
    
    interruption_time = get_date() + ' - ' + get_time() + '\n'
    print("Interruption time:  ", interruption_time)
    print(Sound_data)
    

# Create the CSV
with open(fileName, 'a', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(Sound_data)
    writer.writerow(last_row)
    print("Data appended to .csv file")



data_thread.join()
sound_thread.join()
#timeout_thread.join()

ser.close()  # Close the serial connection after use