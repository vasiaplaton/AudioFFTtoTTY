from subprocess import Popen, PIPE, STDOUT
import threading
from tkinter import *


class CavaListener:
    def __init__(self, config_path, cava_command, show_volume=False):
        self.config_path = config_path
        self.cava_command = cava_command
        self.show_volume = show_volume
        self._p = None
        self.cava_run = False
        self.sink_name = ""
        self.num_of_bars = self._config_parse("bars")
        self.max_value = self._config_parse("ascii_max_range")
        # start cava
        self.start()
        self.cava_run = True
        # input changed listener start
        self._check_input()

    def start(self):
        # start cava with buffer for 1 line
        self._p = Popen([self.cava_command, '-p', self.config_path], stdin=PIPE, stdout=PIPE, stderr=STDOUT, bufsize=1,
                        universal_newlines=True)

    def kill(self):
        self._p.kill()

    def process(self):
        if not self.cava_run:
            return [0]*self.num_of_bars
        for line in self._p.stdout:
            splited = line.split(";")
            # convert array of string to array of int
            desired_array = []
            count = 0
            volume = 0
            for numeric_string in splited[:len(splited)-1]:
                int_value = int(numeric_string)
                desired_array.append(int_value)
                if self.show_volume:
                    if count < 10:
                        volume += int_value*0.4
                    elif 10 <= count < 20:
                        volume += int_value
                    elif count >= 10:
                        volume += int_value * 0.8
                    count += 1
            if self.show_volume:
                desired_array.append(volume/10)
            return desired_array

    def _config_parse(self, name):
        config = open(self.config_path, 'r')
        # check all lines
        for line in config:
            # comments throw out
            if line[0] != ";" and line[0] != "#" and line[0] != "[" and line[0] != "\n":
                if line.find(name) != -1:
                    # write to output array
                    index = line.find("=")
                    return int(line[index+1:])
        raise ValueError("config " + name + "parameter in config file and restart app")

    def _check_input(self):
        list_proc = Popen(['pactl list short sinks'], stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                          universal_newlines=True, shell=TRUE)
        (out, err) = list_proc.communicate()
        out = out.split('\n')
        sink_now = ''
        for line in out:
            if line.find("RUNNING") != -1:
                sink_now = line.split()[1]
        if sink_now != '':
            if self.sink_name != '' and self.sink_name != sink_now:
                # restart cava if sink changed
                self.cava_run = False
                self.kill()
                self.start()
                self.cava_run = True
            self.sink_name = sink_now
        threading.Timer(1, self._check_input).start()

    def __del__(self):
        try:
            self.kill()
        except AttributeError:
            print("already killed")


class Drawer:
    def __init__(self, num_of_bars, max_value, width=800, height=600, show_volume=False):
        # tkinter init
        # window make
        self.root = Tk()
        # Name window
        self.root.title("Cava vis")
        # make Canvas, background green
        self._c = Canvas(self.root, width=width, height=height, bg="Black")
        self._c.grid()
        # focus on canvas to keypress get
        self._c.focus_set()
        # array for bars
        self._bars = []
        self.show_volume = show_volume
        # max value
        self.max_value = max_value
        w, h = self._get_c_geometry()
        if self.show_volume:
            for i in range(0, num_of_bars):
                x1, x2 = self._get_bars_x(i, num_of_bars+1)
                self._bars.append(self._c.create_rectangle(x1, 0, x2, h, fill="White"))
            x1, x2 = self._get_bars_x(num_of_bars, num_of_bars + 1)
            self._bars.append(self._c.create_rectangle(x1, 0, x2, h, fill="Red"))
        else:
            for i in range(0, num_of_bars):
                x1, x2 = self._get_bars_x(i, num_of_bars)
                self._bars.append(self._c.create_rectangle(x1, 0, x2, h, fill="White"))

    def set_values(self, values):
        w, h = self._get_c_geometry()
        for i in range(len(self._bars)):
            x1, x2 = self._get_bars_x(i, len(self._bars))
            self._c.coords(self._bars[i], x1, h - self._map_value(values[i], 0, self.max_value, 0, h), x2, h)

    def _get_bars_x(self, i, num_of_bars):
        w, h = self._get_c_geometry()
        return int((w / (num_of_bars * 2 + 1)) * (i * 2 + 1)), int((w/(num_of_bars*2+1))*(i*2+2))

    def _get_c_geometry(self):
        return self._c.winfo_width(), self._c.winfo_height()

    @staticmethod
    def _map_value(value, from_low, from_high, to_low, to_high):
        return (value - from_low) * (to_high - to_low) // (from_high - from_low) + to_low

    def __del__(self):
        try:
            self.root.destroy()
        except TclError:
            print("already destroyed")


cava = CavaListener(config_path='config_raw', cava_command='./cava/cava', show_volume=True)
drawer = Drawer(num_of_bars=cava.num_of_bars, max_value=cava.max_value, show_volume=True)


def main():
    values = cava.process()
    drawer.set_values(values)
    drawer.root.after(10, main)


main()
drawer.root.mainloop()
