import time
import rtmidi
import sys

# abstraction fot the Nano sync control

command = []
serial_message = [240, 44, 78, 83, 1, 247]  # F0 2C 4E 53 01 F7 - command to return S/N of Nano Sync
query_current_Config = [240, 44, 78, 83, 3, 247]  # F0 2C 4E 53 03 F7 - Queries the nano sync about its current setup
write_new_config = [240, 44, 78, 83, 5, command,  247]  # F0 2C 4E 53 0F [20 data bytes] F7


def select_nanosync(midi_list):
    try:
        for i, elem in enumerate(midi_list):
            if 'Test' in elem:
                print("found ")
                return i
    except IOError:
        input("unable to find nano sync, press enter to exit")
        sys.exit(-1)


def verify_connection(midi):

    for i in range(5):
        return_message = midi.get_message()
        if return_message is not None:
            print(return_message)
            return True
        time.sleep(0.1)
    else:
        input("cannot communicate with the nanosync, press enter to exit")
        sys.exit(-1)


midi_out = rtmidi.MidiOut()
#midi_in = rtmidi.MidiIn()
#midi_in.ignore_types(sysex=False)

available_out_ports = midi_out.get_ports()
#available_in_ports = midi_in.get_ports()

#print(available_out_ports, "\n", available_in_ports)

midi_port_out = select_nanosync(available_out_ports)
#midi_port_in = select_nanosync(available_in_ports)

midi_out.open_port(midi_port_out)
#midi_in.open_port(midi_port_in)

test_command = [240, 44, 78, 83, 5, 1, 1, 2, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 5, 1, 1, 3, 4, 2, 1, 247]
midi_out.send_message(test_command)
#verify_connection(midi_in)





