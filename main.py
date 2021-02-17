from subprocess import Popen, PIPE, STDOUT
import threading
from tkinter import *


class ConfigParser:
    def __init__(self, path):
        self.file = open(path, 'r')
        

class CavaListener:
    def __init__(self, config_path, cava_command):
        self._p = None
        self.sink_name = ""
        self.cava_command = cava_command
        self.config_path = config_path
        self.num_of_bars = self._config_parse("bars")
        self.max_value = self._config_parse("ascii_max_range")
        self.start()
        self._check_input()

    def start(self):
        # start cava with buffer for 1 line
        self._p = Popen([self.cava_command, '-p', self.config_path], stdin=PIPE, stdout=PIPE, stderr=STDOUT, bufsize=1,
                        universal_newlines=True)

    def kill(self):
        self._p.kill()

    def process(self):
        for line in self._p.stdout:
            splited = line.split(";")
            # convert array of string to array of int
            desired_array = []
            for numeric_string in splited[:len(splited)-1]:
                int_value = int(numeric_string)
                desired_array.append(int_value)
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
                print("restarting cava, sink changed")
                self.kill()
                self.start()
            self.sink_name = sink_now
        threading.Timer(1, self._check_input).start()

    def __del__(self):
        try:
            self.kill()
        except AttributeError:
            print("already killed")


class Drawer:
    def __init__(self, num_of_bars, max_value, width=800, height=600):
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
        # max value
        self.max_value = max_value
        w, h = self._get_c_geometry()
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


cava = CavaListener(config_path='config_raw', cava_command='./cava/cava')
drawer = Drawer(num_of_bars=cava.num_of_bars, max_value=cava.max_value)


def main():
    values = cava.process()
    drawer.set_values(values)
    drawer.root.after(10, main)


main()
drawer.root.mainloop()
