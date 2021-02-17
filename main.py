from subprocess import Popen, PIPE, STDOUT
import threading
from tkinter import *


class CavaListener:
    def __init__(self, dynamic_max=False):
        self._p = None
        # TODO parse value from cava config vs hard coding
        self.num_of_bars = 30
        self.max_value = 1000
        if dynamic_max:
            threading.Timer(1, self.find_max).start()

    def start(self):
        # TODO path to config and cava by argument vs hard coding
        # start cava with buffer for 1 line
        self._p = Popen(['./cava/cava', '-p', 'config_raw'], stdin=PIPE, stdout=PIPE, stderr=STDOUT, bufsize=1,
                        universal_newlines=True)

    def process(self):
        for line in self._p.stdout:
            splited = line.split(";")
            # convert array of string to array of int
            desired_array = [int(numeric_string) for numeric_string in splited[:len(splited)-1]]
            return desired_array

    def find_max(self):
        pass

    def __del__(self):
        self._p.kill()


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


cava = CavaListener()
cava.start()
drawer = Drawer(num_of_bars=cava.num_of_bars, max_value=cava.max_value)


def main():
    values = cava.process()
    drawer.set_values(values)
    drawer.root.after(10, main)


main()
drawer.root.mainloop()
