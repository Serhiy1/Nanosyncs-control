<H1>  Rosendahl Nanosyncs control </H1>

This is a library that allows you to programmatically control the rosendahl nanosyncs HD. 

https://rosendahl-studiotechnik.com/nanosyncs.html

This library was created through sniffing and reverse engineering the midi commands being sent between host computer and
the nanosyncs.

Interface with the library is fairly simple. The example below should give you everything that you need to know


    from Nano_sync_control import NanoSync

    """connect to the nanosync, set the HD sync standard to 720 and set the fps 60 and then print the config"""

    example = NanoSync()
    example.set_hd_standard("720p x2 fps")
    example.set_fps("30 fps")
    example.print_current_config() 

 
You can also circumvent the getters and setters by using the `example.send_new_config_raw()`

To do this you will require to know the entire byte structure of the command. 

    byte 0: current cursor position  [placeholder]
    byte 1: INTERNAL = 1, EXT PAL = 2 , EXT NTSC = 3 , EXT.TRI = 4
    byte 2: NTSC = 1, PAL 25 =2, PAL 24 = 3, PAL 23.98= 4
    byte 3: 1080i = 1, 1080p = 2, 1080p x 2fps = 3, 720p = 4, 720p x 2fps = 5
    byte 4: 23.98fps = 1, 24fps = 2, 25fps = 3, 29.97fps = 4, 30fps = 5
    byte 5: SD = 1, HD = 2
    byte 6: SD = 1, HD = 2
    byte 7: SD = 1, HD = 2
    byte 8: SD = 1, HD = 2
    
    byte 9:  follow video = 1, external word FS = 2, external word 1:1 = 3, LTC = 4
    byte 10: 44.1Khz = 1, 48Khz = 2
    byte 11: x1 = 1 , x2 = 1
    byte 12: /1 = 1, /1001 - achieves a 0.1% modifier to value = 1
    byte 13: 23.98fps =1, 24fps =2, 25fps = 3, 29.97= 4, 30fps = 5
    byte 14: 48Khz = 1, 44.1Khz = 2
    byte 15: x1 = 1, +4% = 2, +0.1% = 3, -0.1% - 4,-4% = 5
    byte 16: x1 = 1, x2 = 2, x4 = 3
    byte 17: x1 = 1, x2 = 2, x4 = 3, x256 = 4
    byte 18: x1 = 1, x2 = 2
    byte 19: x1 = 1, x2 = 2
 
 
The library will format the command for you the the relevant system exclusive messages


