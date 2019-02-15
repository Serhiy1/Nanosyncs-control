import sys
import time
import rtmidi


class NanoSync:
    def __init__(self):

        self.serial_number = ""
        self.firmware_version = ""

        # create midi objects fot communication

        self.nanosync_midi_out = rtmidi.MidiOut()
        self.nanosync_midi_in = rtmidi.MidiIn()

        # abstraction for the Nano sync control
        self.cursor_pos = 0              # byte 0: current cursor position  [placeholder]
        self.video_ref = 1               # byte 1: INTERNAL = 1, EXT PAL = 2 , EXT NTSC = 3 , EXT.TRI = 4
        self.video_standard = 1          # byte 2: NTSC = 1, PAL 25 =2, PAL 24 = 3, PAL 23.98= 4
        self.HD_standard = 1             # byte 3: 1080i x 2fps = 1, 1080p = 2, 1080p x 2fps = 3, 720p = 4, 720p x 2fps = 5
        self.FPS = 1                     # byte 4: 23.98fps = 1, 24fps = 2, 25fps = 3, 29.97fps = 4, 30fps = 5
        self.video_1_to_3 = 1            # byte 5: SD = 1, HD = 2
        self.video_4 = 2                 # byte 6: SD = 1, HD = 2
        self.video_5 = 2                 # byte 7: SD = 1, HD = 2
        self.video_6 = 2                 # byte 8: SD = 1, HD = 2

        # audio stuff below, best to leave it all alone
        self.audio_ref = 1               # byte 9:  follow video = 1, external word FS = 2, external word 1:1 = 3, LTC = 4
        self.external_word_fs = 1        # byte 10: 44.1Khz = 1, 48Khz = 2
        self.external_word_fs_x2 = 1     # byte 11: x1 = 1 , x2 = 1
        self.external_word_fs_1 = 1      # byte 12: /1 = 1, /1001 - achieves a 0.1% modifier to value = 1
        self.external_LTC_fps = 1        # byte 13: 23.98fps =1, 24fps =2, 25fps = 3, 29.97= 4, 30fps = 5
        self.audio_sample_rate = 1       # byte 14: 48Khz = 1, 44.1Khz = 2
        self.sample_rate_P_factor = 1    # byte 15: x1 = 1, +4% = 2, +0.1% = 3, -0.1% - 4,-4% = 5
        self.word_multiplier_1_6 = 1     # byte 16: x1 = 1, x2 = 2, x4 = 3
        self.word_multiplier_7_8 = 1     # byte 17: x1 = 1, x2 = 2, x4 = 3, x256 = 4
        self.AES_multiplier = 1          # byte 18: x1 = 1, x2 = 2
        self.SPDIF_multiplier = 1        # byte 19: x1 = 1, x2 = 2

        # important commands used for nan
        self.serial_message = [240, 44, 78, 83, 1, 247]         # F0 2C 4E 53 01 F7 - command to return S/N of Nano Sync
        self.query_current_Config = [240, 44, 78, 83, 3, 247]   # F0 2C 4E 53 03 F7 - Queries the nano sync about its current setup
        self.write_new_config = []                              # F0 2C 4E 53 0F [20 data bytes] F7

        self.video_config = []  # containers for the video variables above, should make it easier to edit
        self.audio_config = []  # containers for the audio variables above, should make it easier to edit

        self.current_config = self.video_config + self.audio_config
        self.command = self.current_config  # gives a base config for users to edit

        self.connect_to_nano_sync()
        self.get_current_config()

    def new_command(self):
        comm_1 = [240, 44, 78, 83, 15]
        comm_2 = [247]
        comm = comm_1 + self.command + comm_2
        return comm

    def connect_to_nano_sync(self):

        # Should initialise the midi in and out ports
        # Should select the correct port from the list of devices
        # Should verify that the connection is successful by sending the return serial device

        self.nanosync_midi_in.ignore_types(sysex=False)
        available_out_ports = self.nanosync_midi_out.get_ports()
        available_in_ports = self.nanosync_midi_in.get_ports()

        self.nanosync_midi_out.open_port(self.select_correct_port(available_out_ports))
        self.nanosync_midi_in.open_port(self.select_correct_port(available_in_ports))

        self.send_message(self.serial_message)
        info = self.receive_message()
        if info is None:
            input("failed to communicate with nanosync, press enter to exit")
            sys.exit(-1)
        else:
            info = info[0]  # midi library returns a tuple with extra data, this strips it
            info = info[5:-1]  # this strips the padding of the return message
            serial_number = info[:4]
            firmware = info[4:]

            for char in serial_number:
                self.serial_number += chr(char)
            for char in firmware:
                self.firmware_version += chr(char)
            self.firmware_version = self.firmware_version[:2] + '.' + self.firmware_version[2:]

            print("connected to NanoSync - serial number: " + self.serial_number + "\n"
                                                                                   "Firmware version " + self.firmware_version)

    def select_correct_port(self, midi_list):

        # rtpmidi returns a list of of midi devices that may be in different orders
        # function selects port based the name

        try:
            for i, elem in enumerate(midi_list):
                if 'NANOSYNCS' in elem:
                    print("found ")
                    return i
        except IOError:
            error = "unable to find nano sync"
            return error

    def send_message(self, message):
        # should use the self midi output port to send the message to the nanoSync
        self.nanosync_midi_out.send_message(message)

    def receive_message(self):
        # should use the self midi input port to send the message nanoSync
        # should return the message
        for i in range(5):
            return_message = self.nanosync_midi_in.get_message()
            if return_message is not None:
                return return_message
            time.sleep(0.1)
        else:
            input("cannot communicate with the nanosync, press enter to exit")
            sys.exit(-1)

    def get_current_config(self):

        # Requests the current using the send message and receive functions
        # strips the return message
        # saves the current config to self variables

        self.nanosync_midi_out.send_message(self.query_current_Config)
        temp = self.receive_message()
        temp = temp[0]  # midi library returns a tuple with extra data, this strips it
        temp = temp[5:-1]  # this strips the padding of the return message

        self.cursor_pos = temp[0]
        self.video_ref = temp[1]
        self.video_standard = temp[2]
        self.HD_standard = temp[3]
        self.FPS = temp[4]
        self.video_1_to_3 = temp[5]
        self.video_4 = temp[6]
        self.video_5 = temp[7]
        self.video_6 = temp[8]

        self.audio_ref = temp[9]
        self.external_word_fs = temp[10]
        self.external_word_fs_x2 = temp[11]
        self.external_word_fs_1 = temp[12]
        self.external_LTC_fps = temp[13]
        self.audio_sample_rate = temp[14]
        self.sample_rate_P_factor = temp[15]
        self.word_multiplier_1_6 = temp[16]
        self.word_multiplier_7_8 = temp[17]
        self.AES_multiplier = temp[18]
        self.SPDIF_multiplier = temp[19]

        self.update_current_config()

    def update_current_config(self):

        self.video_config = [self.cursor_pos, self.video_ref, self.video_standard, self.HD_standard, self.FPS,
                             self.video_1_to_3,
                             self.video_4, self.video_5, self.video_6]
        self.audio_config = [self.audio_ref, self.external_word_fs, self.external_word_fs_x2, self.external_word_fs_1,
                             self.external_LTC_fps, self.audio_sample_rate, self.sample_rate_P_factor,
                             self.word_multiplier_1_6, self.word_multiplier_7_8, self.AES_multiplier,
                             self.SPDIF_multiplier]

        self.current_config = self.video_config + self.audio_config

    def send_new_config(self, command):
        # receives a new config passed in by the user and applies it to the rosendahl
        # Uses the get_current_config method to verify that the config has been sent successfully

        self.get_current_config()
        comparision = self.current_config
        self.command = command

        for i in range(5):
            self.send_message(self.new_command())
            self.get_current_config()
            if comparision != self.current_config:  # This may provide a false positive if the nanosync is pre-configured with the same setting being sent
                print("successfully sent command")
                break
        else:
            print("could not send command")
            time.sleep(0.1)

    def update_config(self):
        self.update_current_config()
        self.command = self.current_config
        self.send_message(self.new_command())
        self.get_current_config()
        self.print_current_config()

    def print_current_config(self):

        # gets the current config and and translates its to people language
        # returns the config in people language

        byte_0 = ["Placeholder"]
        byte_1 = ["INTERNAL", "EXT PAL", "EXT NTSC", "EXT TRI LVL"]
        byte_2 = ["SD standard", "NTSC", "PAL 25", "PAL 24", "PAL 23.98"]
        byte_3 = ["1080i x 2fps", "1080p", "1080p x 2fps", "720p", "720p x 2fps"]
        byte_4 = ["23.98fps", "24fps", "25fps", "29.97fps", "30fps"]
        byte_5 = ["SD", "HD"]
        byte_6 = ["SD", "HD"]
        byte_7 = ["SD", "HD"]
        byte_8 = ["SD", "HD"]
        byte_9 = ["follow video", "external word clock", "external word 1:1", "LTC"]
        byte_10 = ["44.1Khz", "48Khz"]
        byte_11 = ["x1", "x2"]
        byte_12 = ["1/1", "+0.1%"]
        byte_13 = ["23.98 fps", " 24fps", "25fps", "29.97fps", "30fps"]
        byte_14 = ["48Khz", "44.1Khz"]
        byte_15 = ["x1", "+4%", "+0.1%", "-0.1%", "-4%"]
        byte_16 = ["x1", "x2", "x4"]
        byte_17 = ["x1", "x2", "x4", "x256"]
        byte_18 = ["x1", "x2"]
        byte_19 = ["x1", "x2"]

        byte_list = [byte_0, byte_1, byte_2, byte_3, byte_4, byte_5, byte_6, byte_7, byte_8, byte_9, byte_10, byte_11,
                     byte_12, byte_13, byte_14, byte_15, byte_16, byte_17, byte_18, byte_19]

        byte_names_list = ["cursor_pos", "video_ref = ", "video_standard = ", "HD_standard = ", "FPS = ",
                           "video 1 - 3 = ",
                           "video 4 = ", "video 5 = ", "video 6 = ", "audio reference = ", "external word fs = ",
                           "external_word fs x2 = ", "external_word fs 1 = ", "external LTC fps = ",
                           "audio sample rate = ", "sample rate Pull factor = ", "word multiplier 1 to 6 = ",
                           "word multiplier 7 to 8 = ", "AES multiplier = ", "SPDIF multiplier = "]

        i = 0
        for element in self.current_config:
            if i == 0:
                i += 1
                pass
            else:
                # print(byte_names_list[i], byte_list[i][element - 1])
                log_string = str(byte_names_list[i]) + str(byte_list[i][element - 1])
                print(log_string)
                i += 1

    def close(self):
        self.nanosync_midi_out.close_port()
        self.nanosync_midi_in.close_port()

