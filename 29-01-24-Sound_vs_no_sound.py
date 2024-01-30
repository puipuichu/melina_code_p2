'''

Connect IR beams, RFID and feeder for a sound vs. no sound phase in an operant task


Adjust Arduino port and folder/file paths

Reaction types: HIT, WRONG, MISS

HIT: Correct response -> Bird responds during or within 2 sec after a sound was played
WRONG: Pecking forward without a sound or too slow -> NO NOISE .. Sounds just continue 
MISS: Sound was played and Bird does not respond -> no feedback sound ->  Sounds go on if bird is stil there


NOISE ONLY IN THE NEXT PHASES (more then 2 sec after a sound was played) -> NOISE + TIMEOUT (10 sec?)

PROBLEMS: not sure about if bird_on_perch variable makes sense in this way
        
'''
##########################################################################
##### import things ######################################################
##########################################################################

import os, sys
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


folder_path_sound = c.folder_path_sound  # folder in which each consonant sound lasts 0.5 seconds

#file_path_noise = c.file_path_noise ######### NOT NEEDED IN THIS PHASE

sound_files = os.listdir(folder_path_sound)

Sound_data = [] 


random.shuffle(sound_files) # shift in a loop and shuffle new every x sounds; config file for different conditions


arduino_port = c.arduino_port  # Serial port of Arduino for IR beams; 
baud = 9600  # Arduino Uno runs at 9600 baud
fileName = c.fileName_Sound    # Name of the CSV file generated

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
previous_ID = None

last_row = ["11:11:11", "3BXXXXXX", "X", "X", "X", "X"]

sounds_in_folder = 24 ############ CHANGE HERE dependng on the number of files in the folder
sound_counter = 0

data = ""


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

#print_labels = False


#recent_responses = [] # store bird status in the list of recent responses after a sound

##########################################################################
##### define functions ###################################################
##########################################################################

def play_sound(sound_files, folder_path_sound):         # sounds will keep playing as long as bird_on_perch is true.. currently reset after  
    sound_list = []
    global sound_playing, sound_exit_flag, endsound_t
    global sound_counter
    global sounds_in_folder
    global current_sound

    while not data_exit_flag:

        if sound_exit_flag:
            winsound.PlaySound(None, winsound.SND_PURGE)  # Stop all sounds
            #break

        while bird_on_perch:
            ##while data.startswith("3B"): 
            for sound in sound_files:
                print(sound)
                sound_list.append(sound.strip())
                current_sound = sound
                sound_playing = True
                winsound.PlaySound(os.path.join(folder_path_sound, sound), winsound.SND_FILENAME)
                endsound_t = time.time()
                sound_playing = True
                time.sleep(5) # duration between sounds in sec 
                sound_playing = False
                sound_counter = sound_counter + 1
                #print("sound_counter ", sound_counter)

                if sound_counter == sounds_in_folder:
                    random.shuffle(sound_files)
                    sound_counter = 0 # reset the counter
                    print("shuffled new")

                    if sound_exit_flag or bird_on_perch == False:
                        break

   

        #if sound_exit_flag == True:
         #       break 
                       

def send_message(message):      #to activate the feeder later
    ser.write(message.encode())



def read_data():  # new thread to ensure data is read
    prev_data = "nix"
    global data
    while not data_exit_flag:
        data = ser.readline().decode('utf-8').strip()
        #print(data)

        #if data != prev_data: 
         #   print(data)
        time.sleep(0.1)
        prev_data = data
        
def is_sound_playing():
    return sound_playing #flag set in the definition of play_sound()

sound_thread = threading.Thread(target=play_sound, args=(sound_files, folder_path_sound))
sound_thread.daemon = True # to let it run in the background
sound_thread.start()

#one liner doesn't work (cannot join)
#data_thread = threading.Thread(target=read_data, daemon = True).start()
data_thread = threading.Thread(target=read_data)
data_thread.daemon = True
data_thread.start()


try:
    
    ser.timeout = 0.1
    while not data_exit_flag:
        if data:
            print(data)

            current_t = time.time()  # to measure the elapsed time in ms.. timestamp would not be enough
            #print("Current time: ", current_t)
            time_elapsed = current_t - endsound_t #endsound_t is taken above in the play sound loop
            #print("Time elapsed: ", time_elapsed)

            timestamp = get_time() 

            # Check if the bird can be rewarded (it cannot be rewarded if it is still breaking the IR beam after being rewarded)
            if reward_status == 0:

                # Condition 1: noBird (IR beam not broken) -> important here because independent from sounds
                if data == "noBird": 
                    IR_bird_status = data

                #Condition 2: starts with "3B" (bird recoginized by RFID)
                elif data.startswith("3B"):
                        bird_on_perch = True
                        identity = data
                        if identity != previous_ID:
                                previous_ID = data
                                detection_t = time.time()
                                sound_exit_flag = False
                                Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, ""])
                                time.sleep(0.01)
            
                # Condition 3: Bird (IR beam broken)
                elif data == "Bird": 
                        
                    data = IR_bird_status
                    bird_on_perch = True

                    # HIT: sound is over but was presented only two seconds or less ago 
                    if sound_playing == False and time_elapsed <= 2 or sound_playing == True: 
                        print("HIT activate feeder to get a reward")#sound is over but was presented only two seconds or less ago
                        sound_exit_flag = True
                        identity = previous_ID
                        #print ("sound sound_exit_flag = True but bird on perch also True")
                        send_message("motor_on") #command to activate feeder through the arduino
                        reward_status = 1

                        ################################## append data ###############################################
                        Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "HIT"])
                        ##############################################################################################

                        #Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound])
                        time.sleep(3)

                        # future call if bird is still bird in a timespan between
                        #reward_status = 0
                        sound_exit_flag = False
                        #data_exit_flag = False #??????????????????????????

                        '''

                        # HIT: response during the sound but still rewarded
                        elif sound_playing == True: 
                            print("rewarded/sound was playing, activate feeder")
                            send_message("motor_on") #command to activate feeder through the arduino
                            reward_status = 1
                            sound_exit_flag = True
                            data = IR_bird_status
                            identity = previous_ID
                            #print ("sound sound_exit_flag = True but bird on perch also True ")

                        '''

                        
                        
                        print("short timeout to eat")
                        time.sleep(3)

                        
                    '''   
                    NEW IDEA BY MARISA: no noise in this phase -> 

                    elif sound_playing == False and time_elapsed >= 2: #WRONG: Timeout if IR beam is broken too late  -> NOISE -> WRONG        NOT WORKING
                        print("no reward - WRONG response")
                        reward_status = 0
                        winsound.PlaySound(file_path_noise, winsound.SND_FILENAME)
                        current_sound = "NOISE"
                        IR_bird_status = "Bird" #will not be logged otherwise
                        # maybe set bird on perch false?
                        Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "WRONG"])
                    '''

                #MISS: no response where there should be a response -> Timeout but sounds continue afterwards
                #elif sound_playing == False and time_elapsed >= 2:
            
                        
                elif time_elapsed >= 2 and endsound_t != 0: #and reward_status == 1: #data == "noBird" and 
                    print("no reward/too slow or no response")
                    
                    reward_status = 0
                    #sound_exit_flag = True

                    time.sleep(5)
                    print("no SOUNDS")

                    sound_exit_flag = False
                    print("Sounds continued")

                    if data == "noBird" or data == "Bird": #will not be logged otherwise
                        IR_bird_status = data
                    
                    ############## append MISS response to file ###################################################
                    Sound_data.append([timestamp, identity, IR_bird_status, reward_status, current_sound, "MISS"])

                    #endsound_t = 0
                    time_elapsed = 0

                # IR sensor timeout: bird already rewarded by breaking IR beam, timeout until bird leaves IR sensor
                elif reward_status == 1:        #only happens when bird has been rewarded by breaking IR beam 
                    while data != "noBird": #break the loop when bird leaves the IR sensor
                        print("paused until IR beams are free again")
                        sound_exit_flag = True 
                        time.sleep(1)
                                                        
                    # Reset variables
                    reward_status = 0       #reward status is still 1 because this bird just got rewarded and it has to be logged
                    sound_exit_flag = False
                    #previous_ID = None      #reset ID that the same bird can be rewarded again ????????????????
  
        time.sleep(0.1)

except KeyboardInterrupt:
    keyboard_interrupt = True
    print("\nData collection interrupted by user.")
    data_exit_flag = True
    sound_exit_flag = True
    sound_playing = False
    #bird_on_perch = False
    #sound_thread.join()

    
    interruption_time = get_date() + ' - ' + get_time() + '\n'
    print("Interruption time:  ", interruption_time)
    

# Create the CSV
with open(fileName, 'a', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(Sound_data)
    writer.writerow(last_row)



data_thread.join()
sound_thread.join()
#timeout_thread.join()

ser.close()  # Close the serial connection 
f.close() # Close file
    

 
