
'''
Connect IR beams, RFID and feeder for a sound vs. no sound phase in an operant task

Phase 3: Discrimination training: similar to the previous thing but 
rewarded (S+) and not rewarded (S-) sounds (con/dis)
If birds peck forward (2 sec) to S- sounds -> noise + timeout(?)  10 sec


BE CAREFUL: Copied P2 code!!!!

07-02-2024: Sounds added correctly 
NEXT: divide between R and NR sounds (Rewarded or wrong) -> DONE

-> shuffle all sounds -> random selection DONE

NEXT: review by Pui Pui

NEXT: Maybe write list after every loop to the file - not after every condition
      
'''
##########################################################################
##### Program set up #####################################################
##########################################################################

# Import necessary modules
import os
import sys
from random import shuffle, choice
from glob import glob

# Imports for IR beams
import serial
import csv
import time

# Imports for sound
import winsound
import threading
import random

# Import custom configuration module
import config_operant as c

# Set folder paths for stimulus and noise
folder_path_sound_R = c.folder_path_R  # Consonant sound: rewarded
folder_path_sound_NR = c.folder_path_NR  # Dissonant sound: not rewarded
file_path_noise = c.file_path_noise # Noise  

# Get lists of sound filenames and number of sounds
sound_files_R = os.listdir(folder_path_sound_R)
sound_files_NR = os.listdir(folder_path_sound_NR)
sounds_in_folder = c.sounds_in_folder_D # Number of sounds in the specified folder

# Name of the CSV file generated during the experiment
fileName = c.fileName_Phase3  

# Initialize an empty list for sound data
Sound_data = [] 

# Shuffle the lists of sound filenames randomly
random.shuffle(sound_files_R)
random.shuffle(sound_files_NR)

# Configure Arduino communication settings
arduino_port = c.arduino_port  # Serial port of Arduino for IR beams
baud = 9600  # Baud rate for Arduino Uno
ser = serial.Serial(arduino_port, baud)  # Set up serial read
ser.reset_input_buffer()  # Clear input buffer before starting
ser.timeout = 0.25  # Set the timeout for serial communication with Arduino

# Print a message indicating a successful connection to the Arduino port
print("Connected to Arduino port: " + arduino_port)

# Introduce a one-second delay, possibly to allow Arduino initialization
time.sleep(1)

############################################################################
#################### Variables #############################################
############################################################################

sound_exit_flag = False
data_exit_flag = False
sound_playing = False
endsound_t = 0
reward_status = 0
timeout_status = 0
identity = ""   # Initialize identity string variable
IR_bird_status = ""  # Initialize string variable to recognize if IR beam is broken or not
bird_on_perch = False # variable to handle RFID data -> maybe has to be changed later
previous_ID = None
current_sound = None
pause = False
sound_reward = False
sound_counter = 0
data = ""

############################################################################
#################### Time functions ########################################
############################################################################

# Function to get time
def get_time():
    t = time.gmtime()
    milliseconds = int((time.time() % 1) * 1000)
    s = "{:02d}:{:02d}:{:02d}.{:03d}".format(t.tm_hour, t.tm_min, t.tm_sec, milliseconds)
    return s

# Function to get date
def get_date():
	t = time.localtime()
	s = str(t.tm_year) + '/' + str(t.tm_mon) + '/' + str(t.tm_mday)
	return s

##########################################################################
##### Define functions ###################################################
##########################################################################

# Random shuffle function for sound playback
def play_sound(sound_files_R, sound_files_NR, folder_path_sound_R, folder_path_sound_NR):
    global sound_playing, sound_exit_flag, endsound_t, sound_reward
    global sound_counter
    global current_sound
    global pause

    # Main loop for sound playback
    while not data_exit_flag:

        # Continue playback while RFID data starts with "3B" or the bird is on the perch
        while data.startswith("3B") or bird_on_perch:

            # Choose randomly between rewarded (R) and non-rewarded (NR) sound folders
            if random.choice([True, False]):
                folder_path = folder_path_sound_R
                sound_files = sound_files_R
                sound_reward = True  # Rewarded sounds have the sound reward status True
            else:
                folder_path = folder_path_sound_NR
                sound_files = sound_files_NR
                sound_reward = False  # Non-rewarded sounds have the sound reward status False

            sound = random.choice(sound_files)  # Randomly select a sound file from the chosen folder

            # Check for pause state
            while pause and not data_exit_flag:
                time.sleep(1)
                print("Sound pause")

            print(sound)
            current_sound = sound
            sound_playing = True
            winsound.PlaySound(os.path.join(folder_path, sound), winsound.SND_FILENAME)
            endsound_t = time.time()
            time.sleep(7)  # Duration between sounds in seconds
            sound_playing = False
            sound_counter = sound_counter + 1

            # Shuffle sounds if all have been played and the program is not exiting
            if sound_counter == len(sound_files) and not sound_exit_flag:
                random.shuffle(sound_files)
                sound_counter = 0
                print("shuffled new")

            # Shuffle sounds and break out of the loop if the program is exiting
            if sound_exit_flag:
                random.shuffle(sound_files)
                break

# Function to send a message to activate the feeder
def send_message(message):
    ser.write(message.encode())

# Function to read data from the Arduino in a separate thread
def read_data():
    global data
    while not data_exit_flag:
        data = ser.readline().decode('utf-8').strip()
        #data = (sys.stdin.readline()).rstrip()
        time.sleep(0.1)

# Function to check if a sound is currently playing
def is_sound_playing():
    return sound_playing  # Flag set in the definition of play_sound()

# Create and start the sound playback thread
sound_thread = threading.Thread(target = play_sound, args=(sound_files_R, sound_files_NR, folder_path_sound_R, folder_path_sound_NR))
sound_thread.daemon = True  # Run the thread in the background
sound_thread.start()

# Create and start the data reading thread
data_thread = threading.Thread(target = read_data)
data_thread.daemon = True
data_thread.start()

##########################################################################
##### Main loop ##########################################################
##########################################################################

# Check input from arduino (RFID reader and IR sensor)
# Activate feeder to reward bird: when bird respond to sound by breaking IR beam
# Append data to output file

# Open a log file for writing
with open(fileName, "a", encoding = "UTF8", newline = "") as f:
    writer = csv.writer(f)
    writer.writerow([])
    writer.writerow([get_date(), get_time()])
    writer.writerow(["Timestamp", "Identity", "Bird status/IR", "Reward status", "Sound", "Sound type", "Reaction type"])

    # Read input from arduino
    try:
        while not data_exit_flag:

            # Print input from Arduino: noBird, starts with "3B", or Bird
            if data:
                print(data)

                # Check for IR timeout: in IR timeout if bird is breaking IR beam
                if reward_status == 0:

                    # Condition 1: startswith "3B" (bird is on perch) 
                    if data.startswith("3B"): 
                        identity = data

                        # If the bird newly landed on the perch: update variables
                        if identity != previous_ID: 
                            previous_ID = data
                            bird_on_perch = True
                            sound_exit_flag = False
                    
                    # Get current time and time elapsed since the end of the last sound  
                    elif not data.startswith("3B"):                                
                        current_t = time.time()
                        time_elapsed = current_t - endsound_t  # endsound_t is taken above in the play sound loop
                        timestamp = get_time()

                        # Condition 2: noBird (IR beam not broken)
                        if data == "noBird": 

                            # If response time has passed: sound played ended 2 or more seconds ago
                            if time_elapsed >= 2 and endsound_t != 0:
                                IR_bird_status = "noBird"
                                endsound_t = 0                                                                                      
                                bird_on_perch = False                                                                               

                                # MISS: rewarded sound is played but no response
                                if sound_reward == True:
                                    reaction = "MISS"

                                # CORREJ: non rewarded sound is played and no response
                                elif sound_reward == False:
                                    reaction = "CORREJ"

                                # Append data
                                print("no reward - no response") # Print message on screen
                                writer.writerow([timestamp, identity, IR_bird_status, reward_status, current_sound, sound_reward, reaction])

                        # Condition 3: Bird (IR beam broken)
                        elif data == "Bird":

                            # Update variables
                            bird_on_perch = True
                            identity = previous_ID

                            # Condition 3a: MISS (response without sound)
                            if sound_playing == False and time_elapsed >= 2:
                                IR_bird_status = "Bird"
                                reward_status = 0
                                reaction = "MISS"
                                print("no reward - MISS response")

                            # Condition 3b: IR beams broken in time after the sound (HIT or WRONG)
                            else:
                                IR_bird_status = "Bird"

                                # HIT: respond to rewarded sound
                                if sound_reward == True:
                                    
                                    # Update variables
                                    reward_status = 1
                                    reaction = "HIT"

                                    # Reward bird
                                    send_message("motor_on")  # Command to activate feeder through the Arduino
                                    print("HIT correct response - activate feeder to get a reward") # Print message on screen
                                    time.sleep(3)  # Short pause to eat before sounds start again

                                # WRONG: respond to non rewarded sound
                                elif sound_reward == False:

                                    # Update variables
                                    sound_exit_flag = True                  
                                    pause = True
                                    reward_status = 0
                                    reaction = "WRONG"
                                    
                                    # Play noise and print message on screen
                                    winsound.PlaySound(os.path.join(file_path_noise), winsound.SND_FILENAME)
                                    print("Response wrong - WRONG sound") 

                                    # Time out
                                    time.sleep(10)
                                    print("TIMEOUT")
                                    pause = False
                            
                            # Append data
                            writer.writerow([timestamp, identity, IR_bird_status, reward_status, current_sound, sound_reward, reaction])

                # IR timeout function
                elif reward_status == 1:
                    sound_exit_flag = True
                    pause = True

                    # Break the loop when the bird leaves the IR sensor
                    while data != "noBird":
                        print("Paused until IR beams are free again")
                        time.sleep(1)

                    # Reset variables
                    reward_status = 0
                    bird_on_perch = False
                    pause = False
                    time_elapsed = 0

                time.sleep(0.1)

    except KeyboardInterrupt:

        # Update data and song exit flag
        data_exit_flag = True
        sound_exit_flag = True
        
        # Print interruption message on screen
        interruption_time = get_date() + ' - ' + get_time() + '\n'
        print("Data collection interrupted by user at: ", interruption_time)

        # Close threads, serial connection, output file
        data_thread.join() # Threads
        sound_thread.join()
        ser.close() # Serial connection
        f.close() # Output file
        time.sleep(0.1)

# Close mixer and exit program
#mixer.quit()
sys.exit()
