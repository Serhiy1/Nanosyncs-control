import time
import logging
import rtmidi
from bidict import bidict
from collections import namedtuple

class NanoSync:
    def __init__(self):

        self.serial_number = ""
        self.firmware_version = ""

        # create midi objects fot communication

        self.nanosync_midi_out = rtmidi.MidiOut()
        self.nanosync_midi_in = rtmidi.MidiIn()

        self.midi_in_port = None
        self.midi_out_port = None
        self._select_correct_ports()

        # important commands used for NanoSyncs
        self.serial_message = [1]         # F0 2C 4E 53 01 F7 - command to return S/N of Nano Sync and firmware version
        self.query_current_Config = [3]   # F0 2C 4E 53 03 F7 - Queries the nano sync about its current setup

        # abstraction for the Nano sync control

        # <editor-fold desc="Settings dictionaries">
        self.video_ref                          = bidict({"internal": 1, "external pal": 2, "external ntsc": 3, "external tri": 4})
        self.video_standard                     = bidict({"ntsc": 1, "pal 25": 2, "pal 24": 3, "pal 23.98": 4})
        self.HD_standard                        = bidict({"1080i x2 fps": 1, "1080p x1 fps": 2, "1080p x2 fps": 3, "720p x1 fps": 4, "720p x2 fps": 5})
        self.FPS                                = bidict({"23.98 fps": 1, "24 fps": 2, "25 fps": 3, "29.97 fps": 4, "30 fps": 5})
        self.video_definition                   = bidict({"SD" : 1, "HD": 2})

        self.audio_ref                          = bidict({"follow video": 1, "external word clock": 2, "external word 1:1": 3, "LTC": 4})
        self.external_word_fs                   = bidict({"44.1 khz": 1, "48 khz": 2})
        self.external_word_fs_multiplier        = bidict({"x1": 1, "x2": 2})
        self.external_word_fs_modifier          = bidict({"1/1": 1, "+0.1%": 2})
        self.external_LTC_fps                   = bidict({"23.98 fps": 1, " 24 fps": 2, "25 fps": 3, "29.98 fps": 4, "30 fps": 5})
        self.audio_sample_rate                  = bidict({"48 khz": 1, "44.1 khz": 2})
        self.audio_sample_rate_modifier         = bidict({"x1": 1, "+4%": 2, "+0.1%": 3, "-0.1%": 4, "-4%": 5})
        self.word_multiplier_1_6                = bidict({"x1": 1, "x2": 2, "x4": 3})
        self.word_multiplier_7_8                = bidict({"x1": 1, "x2": 2, "x4": 4, "x256": 5})
        self.AES_multiplier                     = bidict({"x1": 1, "x2": 2})
        self.SPDIF_multiplier                   = bidict({"x1": 1, "x2": 2})
        # </editor-fold>

        # Setting some default values

        self.cursor_pos                             = 0 # Placeholder
        self.video_ref_setting                      = self.video_ref["internal"]
        self.video_standard_setting                 = self.video_standard["ntsc"]
        self.HD_standard_setting                    = self.HD_standard["1080p x2 fps"]
        self.FPS_setting                            = self.FPS["30 fps"]
        self.video_1_to_3_setting                   = self.video_definition["HD"]
        self.video_4_setting                        = self.video_definition["HD"]
        self.video_5_setting                        = self.video_definition["HD"]
        self.video_6_setting                        = self.video_definition["HD"]

        # audio stuff below, best to leave it all alone
        self.audio_ref_setting                      = self.audio_ref["follow video"]
        self.external_word_fs_setting               = self.external_word_fs["44.1 khz"]
        self.external_word_fs_multiplier_setting    = self.external_word_fs_multiplier["x1"]
        self.external_word_fs_modifier_setting      = self.external_word_fs_modifier["1/1"]
        self.external_LTC_fps_setting               = self.external_LTC_fps["23.98 fps"]
        self.audio_sample_rate_setting              = self.audio_sample_rate["48 khz"]
        self.audio_sample_rate_modifier_setting     = self.audio_sample_rate_modifier["x1"]
        self.word_multiplier_1_6_setting            = self.word_multiplier_1_6["x1"]
        self.word_multiplier_7_8_setting            = self.word_multiplier_7_8["x1"]
        self.AES_multiplier_setting                 = self.AES_multiplier["x1"]
        self.SPDIF_multiplier_setting               = self.SPDIF_multiplier["x1"]

        self.current_config = None  # Puts all the settings above into a list
        self._update_current_config()

        self._connect()
        self._get_current_config()

    def _update_current_config(self):
        """ Updates the current config list """

        self.current_config =   [self.cursor_pos,
                                self.video_ref_setting,
                                self.video_standard_setting,
                                self.HD_standard_setting,
                                self.FPS_setting,
                                self.video_1_to_3_setting,
                                self.video_4_setting,
                                self.video_5_setting,
                                self.video_6_setting,
                                self.audio_ref_setting,
                                self.external_word_fs_setting,
                                self.external_word_fs_multiplier_setting,
                                self.external_word_fs_modifier_setting,
                                self.external_LTC_fps_setting,
                                self.audio_sample_rate_setting,
                                self.audio_sample_rate_modifier_setting,
                                self.word_multiplier_1_6_setting,
                                self.word_multiplier_7_8_setting,
                                self.AES_multiplier_setting,
                                self.SPDIF_multiplier_setting]

    def _send_message(self, message, new_config=False):
        """Formats with the midi system exclusive header and footer then sends the command via the midi out"""

        if new_config is False:
            header = [240, 44, 78, 83]
            footer = [247]
        else: # if a new config is being sent the header needs to changed
            header = [240, 44, 78, 83, 15]
            footer = [247]

        message = header + message + footer
        self.nanosync_midi_out.send_message(message)

    def _receive_message(self):
        """Makes 5 attempts to read a message from the midi buffer - If nothing is found an IO error is raised"""

        for i in range(5):
            return_message = self.nanosync_midi_in.get_message()
            if return_message is not None:
                return return_message
            time.sleep(0.1)
        else:
            raise IOError("did not receive message from Nanosync after attempts")

    def _get_current_config(self):
        """Function sends the get current config command to nanosyncs, reads data back, formats it and then saves data
         to each variable """


        self._send_message(self.query_current_Config)
        received_config = self._receive_message()
        # midi library return a tuple containing meta data and a list of all the settings
        received_config = received_config[0]  # strip meta data
        received_config = received_config[5:-1]  # Strips the midi system exclusive header and footer

        self.cursor_pos                             = received_config[0]
        self.video_ref_setting                      = received_config[1]
        self.video_standard_setting                 = received_config[2]
        self.HD_standard_setting                    = received_config[3]
        self.FPS_setting                            = received_config[4]
        self.video_1_to_3_setting                   = received_config[5]
        self.video_4_setting                        = received_config[6]
        self.video_5_setting                        = received_config[7]
        self.video_6_setting                        = received_config[8]

        self.audio_ref_setting                      = received_config[9]
        self.external_word_fs_setting               = received_config[10]
        self.external_word_fs_multiplier_setting    = received_config[11]
        self.external_word_fs_modifier_setting      = received_config[12]
        self.external_LTC_fps_setting               = received_config[13]
        self.audio_sample_rate_setting              = received_config[14]
        self.audio_sample_rate_modifier_setting     = received_config[15]
        self.word_multiplier_1_6_setting            = received_config[16]
        self.word_multiplier_7_8_setting            = received_config[17]
        self.AES_multiplier_setting                 = received_config[18]
        self.SPDIF_multiplier_setting               = received_config[19]

        self._update_current_config()

    def _select_correct_ports(self):
        available_out_ports = self.nanosync_midi_out.get_ports()
        available_in_ports = self.nanosync_midi_in.get_ports()

        # rtpmidi returns a list of of midi devices that may be in different orders
        # function selects port based the name

        for i, elem in enumerate(available_in_ports):
            if 'NANOSYNCS' in elem:
                print("found nanosync in port on %i" % i)
                self.midi_in_port = i
                break
        else:
            raise IOError("unable to find nano sync midi out port")

        for i, elem in enumerate(available_out_ports):
            if 'NANOSYNCS' in elem:
                print("found nanosync out port on %i" % i)
                self.midi_out_port = i
                break
        else:
            raise IOError("unable to find nano sync midi in port")

    def _connect(self):

        # Should initialise the midi in and out ports
        # Should select the correct port from the list of devices
        # Should verify that the connection is successful by sending the return serial device

        self.nanosync_midi_in.ignore_types(sysex=False) # Allow system exclusive commands to be sent

        self.nanosync_midi_out.open_port(self.midi_out_port)
        self.nanosync_midi_in.open_port(self.midi_in_port)

        self._send_message(self.serial_message)
        info = self._receive_message()
        if info is None:
            raise IOError("failed to communicate with nanosync")

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

            print("connected to NanoSync")
            print("serial number: %s" % self.serial_number)
            print("Firmware version %s" %  self.firmware_version)

    def disconnect(self):
        self.nanosync_midi_out.close_port()
        self.nanosync_midi_in.close_port()

    def print_current_config(self):
        """Prints the current config to console - used for user readability"""
        self._get_current_config()

        print("video ref: %s" %                   self.video_ref.inverse[self.video_ref_setting])
        print("video standard: %s" %              self.video_standard.inverse[self.video_standard_setting])
        print("HD standard: %s" %                 self.HD_standard.inverse[self.HD_standard_setting])
        print("FPS: %s" %                         self.FPS.inverse[self.FPS_setting])
        print("SDI out 1 to 3: %s" %              self.video_definition.inverse[self.video_1_to_3_setting])
        print("SDI out 4: %s" %                   self.video_definition.inverse[self.video_4_setting])
        print("SDI out 5: %s" %                   self.video_definition.inverse[self.video_5_setting])
        print("SDI out 6: %s" %                   self.video_definition.inverse[self.video_6_setting])

        print("Audio ref: %s" %                   self.audio_ref.inverse[self.audio_ref_setting])
        print("External word: %s" %               self.external_word_fs.inverse[self.external_word_fs_setting])
        print("External word multiplier: %s" %    self.external_word_fs_multiplier.inverse[self.external_word_fs_multiplier_setting])
        print("External word fs 1: %s" %          self.external_word_fs_modifier.inverse[self.external_word_fs_modifier_setting])
        print("External LTC fps: %s" %            self.external_LTC_fps.inverse[self.external_LTC_fps_setting])
        print("Audio sample rate: %s" %           self.audio_sample_rate.inverse[self.audio_sample_rate_setting])
        print("Sample rate pull factor: %s" %     self.audio_sample_rate_modifier.inverse[self.audio_sample_rate_modifier_setting])
        print("word mult 1 to 6: %s" %            self.word_multiplier_1_6.inverse[self.word_multiplier_1_6_setting])
        print("word mult 7 to 8: %s" %            self.word_multiplier_7_8.inverse[self.word_multiplier_7_8_setting])
        print("AES mult: %s" %                    self.AES_multiplier.inverse[self.AES_multiplier_setting])
        print("SPDIF mult: %s" %                  self.SPDIF_multiplier.inverse[self.SPDIF_multiplier_setting])

    def get_current_refresh_rate(self):
        """Returns a named tuple containing the numerator and denominator to calculate the refresh rate"""

        # self.HD_standard_setting = 1  # byte 3: 1080i x 2fps = 1, 1080p = 2, 1080p x 2fps = 3, 720p = 4, 720p x 2fps = 5
        # self.FPS_setting = 1          # byte 4: 23.98fps = 1, 24fps = 2, 25fps = 3, 29.97fps = 4, 30fps = 5

        fps_dict = {
            1: 23.98,
            2: 24,
            3: 25,
            4: 29.97,
            5: 30}

        tuple_dict = {

            60: ("60", "1"),
            50: ("50", "1"),
            48: ("48", "1"),
            30: ("30", "1"),
            25: ("25", "1"),
            24: ("24", "1"),

            59.94: ("60000", "1001"),
            47.96: ("48000", "1001"),
            29.97: ("30000", "1001"),
            23.98: ("24000", "1001")}

        self._get_current_config()  # Make sure we have the latest data

        refresh_rate = fps_dict.get(self.FPS_setting)

        if self.HD_standard_setting in [3, 5]:  # if HD standard is 1080p x 2fps or 720p x 2fps
            refresh_rate *= 2

            refresh_rate_ntp = namedtuple("refresh rate", "numerator denominator")
            return_tuple = refresh_rate_ntp(tuple_dict.get(refresh_rate))
            return return_tuple

        else:

            refresh_rate_ntp = namedtuple("refresh rate", "numerator denominator")
            return_tuple = refresh_rate_ntp(tuple_dict.get(refresh_rate))
            return return_tuple

    def send_new_config_raw(self, new_config):
        """Accepts a list of 20 values corresponding to each of the settings of the nanosyncs """

        # some basic parameter checking
        if type(new_config) is not list:
            print("Command has to be a list")
            return
        if len(new_config) is not 20:
            print("command has to 20 items long ")

        # gets the latest state of the nanosync configuration
        self._get_current_config()
        comparision = self.current_config

        if new_config == comparision:
            print("Nanosyncs already has identical config set, skipping sending the new config ")
        else:
            for i in range(5):
                self._send_message(new_config, new_config= True)
                self._get_current_config()
                if new_config == self.current_config:  # This may provide a false positive if the nanosync is pre-configured with the same setting being sent
                    print("successfully sent command")
                    break
            else:
                print("!!! warning - detected no change in the config of the Nanosync message send may of failed")
                time.sleep(0.1)

    def set_video_ref(self, setting):

        if setting in ["internal", "external pal", "external ntsc", "external tri"]:
            self.video_ref_setting = self.video_ref[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set video ref to %s " % setting)
        else:
            print("invalid setting has been given for video ref")

    def set_video_standard(self, setting):

        if setting in ["ntsc", "pal 25", "pal 24", "pal 23.98"]:
            self.video_standard_setting = self.video_standard[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set video standard to %s " % setting)
        else:
            print("invalid setting has been given for video standard")

    def set_hd_standard(self, setting):

        if setting in ["1080i x2 fps", "1080p x1 fps", "1080p x2 fps", "720p x1 fps", "720p x2 fps"]:
            self.HD_standard_setting = self.HD_standard[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)
            print("set HD standard to %s " % setting)
        else:
            print("invalid setting has been given for HD standard")

    def set_fps(self, setting):

        if setting in ["23.98 fps", "24 fps", "25 fps", "29.97 fps", "30 fps"]:
            self.FPS_setting = self.FPS[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set FPS to %s " % setting)
        else:
            print("invalid setting has been given for FPS")

    def set_sdi_out_1_to_3(self, setting):

        if setting in ["SD", "HD"]:
            self.video_1_to_3_setting = self.video_definition[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set set SDI out 1 to 3 to %s " % setting)
        else:
            print("invalid setting has been given for SDI out 1 to 3")

    def set_sdi_out_4(self, setting):

        if setting in ["SD", "HD"]:
            self.video_4_setting= self.video_definition[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set SDI out 4 to %s " % setting)
        else:
            print("invalid setting has been given for SDI out 4")

    def set_sdi_out_5(self, setting):

        if setting in ["SD", "HD"]:
            self.video_5_setting= self.video_definition[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set SDI out 5 to %s " % setting)
        else:
            print("invalid setting has been given for SDI out 5")

    def set_sdi_out_6(self, setting):

        if setting in ["SD", "HD"]:
            self.video_6_setting= self.video_definition[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set SDI out 5 to %s " % setting)
        else:
            print("invalid setting has been given for SDI out 5")

    def set_audio_reference(self, setting):

        if setting in ["follow video", "external word clock", "external word 1:1", "LTC"]:
            self.audio_ref_setting= self.audio_ref[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set audio reference to %s " % setting)
        else:
            print("invalid setting has been given for audio reference")

    def set_external_word_fs(self, setting):

        if setting in ["44.1 khz", "48 khz"]:
            self.external_word_fs_setting = self.external_word_fs[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set external word FS to %s " % setting)
        else:
            print("invalid setting has been given external word FS")

    def set_external_word_multiplier(self, setting):

        if setting in ["x1", "x2"]:
            self.external_word_fs_multiplier_setting = self.external_word_fs_multiplier[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set external word multiplier to %s " % setting)
        else:
            print("invalid setting has been given for external word multiplier")

    def set_external_word_modifier(self, setting):

        if setting in ["1/1", "+0.1%"]:
            self.external_word_fs_modifier_setting = self.external_word_fs_modifier[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set external word modifier to %s " % setting)
        else:
            print("invalid setting has been given for external word modifier")

    def set_external_ltc_fps(self, setting):

        if setting in ["23.98 fps", " 24 fps", "25 fps", "29.98 fps", "30 fps"]:
            self.external_LTC_fps_setting = self.external_LTC_fps[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set external LTC FPS to %s " % setting)
        else:
            print("invalid setting has been given for external LTC FPS")

    def set_audio_sample_rate(self, setting):

        if setting in ["48 khz", "44.1 khz"]:
            self.audio_sample_rate_setting = self.audio_sample_rate[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set audio sample rate to %s " % setting)
        else:
            print("invalid setting has been given for the audio sample rate")

    def set_audio_sample_rate_modifier(self, setting):

        if setting in ["x1", "+4%", "+0.1%", "-0.1%", "-4%"]:
            self.audio_sample_rate_modifier_setting = self.audio_sample_rate_modifier[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set audio sample rate modifier to %s " % setting)
        else:
            print("invalid setting has been given for audio sample rate modifier ")

    def set_word_multiplier_1_6(self, setting):

        if setting in ["x1", "x2", "x4"]:
            self.word_multiplier_1_6_setting = self.word_multiplier_1_6[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set word multiplier 1 to 6 to %s " % setting)
        else:
            print("invalid setting has been given word multiplier 1 to 6")

    def set_word_multiplier_7_8(self, setting):

        if setting in ["x1", "x2", "x4", "x256"]:
            self.word_multiplier_7_8_setting = self.word_multiplier_7_8[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)

            print("set word multiplier 7 to 8 to %s " % setting)
        else:
            print("invalid setting has been given for word multiplier 7 to 8")

    def set_AES_multiplier(self, setting):

        if setting in ["x1", "x2"]:
            self.AES_multiplier_setting = self.AES_multiplier[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)
            print("set AES multiplier to %s " % setting)
        else:
            print("invalid setting has been given for AES multiplier")

    def set_SPDIF_multiplier(self, setting):
        
        if setting in ["x1", "x2"]:
            self.SPDIF_multiplier_setting = self.SPDIF_multiplier[setting]
            self._update_current_config()
            self.send_new_config_raw(self.current_config)
            print("set SPDIF multiplier to %s " % setting)
        else:
            print("invalid setting has been given for SPDIF multiplier")

    def get_video_ref(self):
        return self.video_ref.inverse[self.video_ref_setting]

    def get_video_standard(self):
        return self.video_standard.inverse[self.video_standard_setting]

    def get_hd_standard(self):
        return self.HD_standard.inverse[self.HD_standard_setting]

    def get_fps(self):
        return self.FPS.inverse[self.FPS_setting]

    def get_sdi_out_1_to_3(self):
        return self.video_definition.inverse[self.video_1_to_3_setting]

    def get_sdi_out_4(self):
        return self.video_definition.inverse[self.video_4_setting]

    def get_sdi_out_5(self):
        return self.video_definition.inverse[self.video_5_setting]

    def get_sdi_out_6(self):
        return self.video_definition.inverse[self.video_6_setting]

    def get_audio_ref(self):
        return self.audio_ref.inverse[self.audio_ref_setting]

    def get_external_word_fs(self):
        return self.external_word_fs.inverse[self.external_word_fs_setting]

    def get_external_word_fs_multiplier(self):
        return self.external_word_fs_multiplier.inverse[self.external_word_fs_multiplier_setting]

    def get_external_word_fs_modifier(self):
        return self.external_word_fs_modifier.inverse[self.external_word_fs_modifier_setting]

    def get_external_LTC_fps(self):
        return self.external_LTC_fps.inverse[self.external_LTC_fps_setting]

    def get_audio_sample_rate(self):
        return self.audio_sample_rate.inverse[self.audio_sample_rate_setting]

    def get_audio_sample_rate_modifier(self):
        return self.audio_sample_rate_modifier.inverse[self.audio_sample_rate_modifier_setting]

    def get_word_multiplier_1_6(self):
        return self.word_multiplier_1_6.inverse[self.word_multiplier_1_6_setting]

    def get_word_multiplier_7_8(self):
        return self.word_multiplier_7_8.inverse[self.word_multiplier_7_8_setting]

    def get_AES_multiplier(self):
        return self.AES_multiplier.inverse[self.AES_multiplier_setting]

    def get_SPDIF_multiplier(self):
        return self.SPDIF_multiplier.inverse[self.SPDIF_multiplier_setting]
