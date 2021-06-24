from subprocess import Popen, PIPE, STDOUT
import threading
from tkinter import *
import signal


class CavaListener:
    def __init__(self, config_path, cava_command, show_volume=False):
        self.config_path = config_path
        self.cava_command = cava_command
        self.show_volume = show_volume
        self._p = None
        self.sink_name = ""
        self.num_of_bars = self._config_parse("bars")
        self.max_value = self._config_parse("ascii_max_range")
        # start cava
        self.start_cava()
        # input changed listener start
        self.thread = threading.Timer(1, self._check_input)
        self.thread.start()

    def start_cava(self):
        # start cava with buffer for 1 line
        self._p = Popen([self.cava_command, '-p', self.config_path], stdin=PIPE, stdout=PIPE, stderr=STDOUT, bufsize=1,
                        universal_newlines=True)

    def kill_cava(self):
        try:
            self._p.kill()
        except AttributeError:
            print("cava already killed")

    def process(self):
        if self._p is None:
            return
        for line in self._p.stdout:
            splited = line.split(";")
            desired_array = []
            # convert array of string to array of int
            count = 0
            volume = 0
            for numeric_string in splited[:len(splited) - 1]:
                int_value = int(numeric_string)
                desired_array.append(int_value)
                if self.show_volume:
                    if count < 10:
                        volume += int_value * 0.4
                    elif 10 <= count < 20:
                        volume += int_value
                    elif count >= 10:
                        volume += int_value * 0.8
                    count += 1
            if self.show_volume:
                desired_array.append(volume / 10)
            return desired_array
        return

    def _config_parse(self, name):
        config = open(self.config_path, 'r')
        # check all lines
        for line in config:
            # comments throw out
            if line[0] != ";" and line[0] != "#" and line[0] != "[" and line[0] != "\n":
                if line.find(name) != -1:
                    # write to output array
                    index = line.find("=")
                    return int(line[index + 1:])
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
                self.kill_cava()
                self.start_cava()
            self.sink_name = sink_now
        self.thread = threading.Timer(1, self._check_input)
        self.thread.start()

    def __del__(self):
        print("cava class destroyed")
        self.kill_cava()
        try:
            self.thread.cancel()
        except AttributeError:
            print("thread already killed")


class Drawer:
    def __init__(self, num_of_bars, max_value, width=800, height=600, show_volume=False, execute_on_close=None):
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
        # prepare for close
        self._prepare_for_close(execute_on_close)
        # array for bars
        self._bars = []
        self.show_volume = show_volume
        # max value
        self.max_value = max_value
        w, h = self._get_c_geometry()
        if self.show_volume:
            for i in range(0, num_of_bars):
                x1, x2 = self._get_bars_x(i, num_of_bars + 1)
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
        return int((w / (num_of_bars * 2 + 1)) * (i * 2 + 1)), int((w / (num_of_bars * 2 + 1)) * (i * 2 + 2))

    def _get_c_geometry(self):
        return self._c.winfo_width(), self._c.winfo_height()

    @staticmethod
    def _map_value(value, from_low, from_high, to_low, to_high):
        return (value - from_low) * (to_high - to_low) // (from_high - from_low) + to_low

    def _prepare_for_close(self, execute_on_close):
        # on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        # sigkill close

        def sigkill_handler(_sig, _frame):
            self._on_closing()

        signal.signal(signal.SIGINT, sigkill_handler)
        # external function that executed on close
        self.execute_on_close = execute_on_close

    def _on_closing(self):
        print("window closed")
        self.__del__()
        self.execute_on_close()

    def __del__(self):
        try:
            self.root.destroy()
        except TclError:
            print("already destroyed")


cava = CavaListener(config_path='config_raw', cava_command='./cava/cava', show_volume=True)
drawer = Drawer(num_of_bars=cava.num_of_bars, max_value=cava.max_value, show_volume=True, execute_on_close=cava.__del__)


def main():
    values = cava.process()
    if values is not None:
        drawer.set_values(values)
    drawer.root.after(10, main)


main()
drawer.root.mainloop()
