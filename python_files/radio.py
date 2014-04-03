#!/usr/bin/env python3
# requires `mplayer` to be installed
from time import sleep
import os
import sys
import signal
import shlex
import math
import lirc

PY3 = sys.version_info[0] >= 3
if not PY3:
    print("Radio only works with `python3`.")
    sys.exit(1)

from threading import Barrier  # must be using Python 3
import subprocess
import pifacecommon
import pifacecad
from pifacecad.lcd import LCD_WIDTH


UPDATE_INTERVAL = 1

STATIONS = [
    # {'name': "6 Music",
    #  'source': 'http://www.bbc.co.uk/radio/listen/live/r6_aaclca.pls',
    #  'info': 'http://www.bbc.co.uk/radio/player/bbc_6music'},
     {'name': "Radio 1 NL",
      'source': 'http://145.58.53.153:80/radio1-bb-mp3',
      'info': None},
    {'name': "Radio 2 NL",
      'source': 'http://145.58.53.153:80/radio2-bb-mp3',
      'info': None},
    {'name': "3FM",
      'source': 'http://145.58.53.153:80/3fm-bb-mp3',
      'info': None},
    {'name': "Radio 4 NL",
      'source': 'http://145.58.53.153:80/radio4-bb-mp3',
      'info': None},
    {'name': "Radio 5 NL",
      'source': 'http://145.58.53.153:80/radio5-bb-mp3',
      'info': None},
    {'name': "Radio 6 NL",
      'source': 'http://145.58.53.153:80/radio6-bb-mp3',
      'info': None},
    {'name': "FunX Reggae",
      'source': 'http://145.58.53.153:80/funx-reggae-bb-mp3',
      'info': None},
    {'name': "SkyRadio 101FM",
     'source': 'http://8543.live.streamtheworld.com/SKYRADIOAAC_SC',
     'info': None},
    {'name': "Mellow jazz",
     'source': 'http://pub1.jazzradio.com:80/jr_mellowjazz_aacplus?1aba074d8894838f3cdccfe5',
     'info': None}
]

PLAY_SYMBOL = pifacecad.LCDBitmap(
    [0x10, 0x18, 0x1c, 0x1e, 0x1c, 0x18, 0x10, 0x0])
PAUSE_SYMBOL = pifacecad.LCDBitmap(
    [0x0, 0x1b, 0x1b, 0x1b, 0x1b, 0x1b, 0x0, 0x0])
INFO_SYMBOL = pifacecad.LCDBitmap(
    [0x6, 0x6, 0x0, 0x1e, 0xe, 0xe, 0xe, 0x1f])
MUSIC_SYMBOL = pifacecad.LCDBitmap(
    [0x2, 0x3, 0x2, 0x2, 0xe, 0x1e, 0xc, 0x0])

PLAY_SYMBOL_INDEX = 0
PAUSE_SYMBOL_INDEX = 1
INFO_SYMBOL_INDEX = 2
MUSIC_SYMBOL_INDEX = 3


class Radio(object):
    def __init__(self, cad, start_station=0):
        self.current_station_index = start_station
        self.playing_process = None

        # set up cad
        cad.lcd.blink_off()
        cad.lcd.cursor_off()
        cad.lcd.backlight_on()

        cad.lcd.store_custom_bitmap(PLAY_SYMBOL_INDEX, PLAY_SYMBOL)
        cad.lcd.store_custom_bitmap(PAUSE_SYMBOL_INDEX, PAUSE_SYMBOL)
        cad.lcd.store_custom_bitmap(INFO_SYMBOL_INDEX, INFO_SYMBOL)
        self.cad = cad

    @property
    def current_station(self):
        """Returns the current station dict."""
        return STATIONS[self.current_station_index]

    @property
    def playing(self):
        return self._is_playing

    @playing.setter
    def playing(self, should_play):
        if should_play:
            self.play()
        else:
            self.stop()

    @property
    def text_status(self):
        """Returns a text represenation of the playing status."""
        if self.playing:
            return "Now Playing"
        else:
            return "Stopped"

    def play(self):
        """Plays the current radio station."""
        print("Playing {}.".format(self.current_station['name']))
        play_command = "mplayer -quiet {stationsource}".format(
            stationsource=self.current_station['source'])
        self.playing_process = subprocess.Popen(
            play_command,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid)
        self._is_playing = True
        self.update_display()

    def stop(self):
        """Stops the current radio station."""
        print("Stopping radio.")
        os.killpg(self.playing_process.pid, signal.SIGTERM)
        self._is_playing = False
        self.update_playing()

    def change_station(self, new_station_index):
        """Change the station index."""
        was_playing = self.playing
        if was_playing:
            self.stop()
        self.current_station_index = new_station_index % len(STATIONS)
        if was_playing:
            self.play()

    def next_station(self, event=None):
        self.change_station(self.current_station_index + 1)

    def previous_station(self, event=None):
        self.change_station(self.current_station_index - 1)


    def inc_volume(self, event=None):
        """Increment volume by x"""
        print("Volume +")
        """TODO: Check value validity"""
        subprocess.Popen(
            "amixer set PCM 500+",
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid)


    def dec_volume(self, event=None):
        """Decrement volume by x"""
        print("Volume -")
        """TODO: Check value validity"""
        subprocess.Popen(
            "amixer set PCM 500-",
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid)

    def update_display(self):
        self.update_station()
        self.update_playing()
        # self.update_volume()

    def update_playing(self):
        """Updated the playing status."""
        #message = self.text_status.ljust(LCD_WIDTH-1)
        #self.cad.lcd.write(message)
        if self.playing:
            char_index = PLAY_SYMBOL_INDEX
        else:
            char_index = PAUSE_SYMBOL_INDEX

        self.cad.lcd.set_cursor(0, 0)
        self.cad.lcd.write_custom_bitmap(char_index)

    def update_station(self):
        """Updates the station status."""
        message = self.current_station['name'].ljust(LCD_WIDTH-1)
        self.cad.lcd.set_cursor(1, 0)
        self.cad.lcd.write(message)

    def update_volume(self):
        """Updates the display's volume status."""
        out = check_output(["amixer", "get PCM"])
        parse = split(out,'[')
        parse = rsplit(parsing,']')
        print("Vol update:{s}").format(s=parse)
        self.cad.lcd.set_cursor(1,1)
        seld.cad.lcd.write(parse)

    def toggle_playing(self, event=None):
        if self.playing:
            self.stop()
        else:
            self.play()

    def close(self):
        self.stop()
        self.cad.lcd.clear()
        self.cad.lcd.backlight_off()


def radio_preset_switch(event):
    global radio
    radio.change_station(event.pin_num)


def radio_preset_ir(event):
    global radio
    radio.change_station(int(event.ir_code))


if __name__ == "__main__":
    # test for mplayer
    try:
        subprocess.call(["mplayer"], stdout=open('/dev/null'))
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            print(
                "MPlayer was not found, install with "
                "`sudo apt-get install mplayer`")
            sys.exit(1)
        else:
            raise  # Something else went wrong while trying to run `mplayer`

    cad = pifacecad.PiFaceCAD()
    global radio
    radio = Radio(cad)
    radio.play()

    # listener cannot deactivate itself so we have to wait until it has
    # finished using a barrier.
    global end_barrier
    end_barrier = Barrier(2)

    # wait for button presses
    switchlistener = pifacecad.SwitchEventListener(chip=cad)
    # for pstation in range(4):
    #     switchlistener.register(
    #         pstation, pifacecad.IODIR_ON, radio_preset_switch)
    #switchlistener.register(4, pifacecad.IODIR_ON, end_barrier.wait)
    switchlistener.register(2, pifacecad.IODIR_ON, radio.dec_volume)
    switchlistener.register(3, pifacecad.IODIR_ON, radio.inc_volume)
    switchlistener.register(5, pifacecad.IODIR_ON, radio.toggle_playing)
    switchlistener.register(6, pifacecad.IODIR_ON, radio.previous_station)
    switchlistener.register(7, pifacecad.IODIR_ON, radio.next_station)

    switchlistener.activate()

    end_barrier.wait()  # wait unitl exit

    # exit
    radio.close()
    switchlistener.deactivate()
