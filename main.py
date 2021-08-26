from subprocess import Popen, PIPE, STDOUT
import threading
from tkinter import *
import signal
import serial
import serial.tools.list_ports


class CavaListener:
    def __init__(self, config_path, cava_command):
        self.config_path = config_path
        self.cava_command = cava_command
        self._p = None
        self.sink_name = ""

        self.num_of_bars = self._config_parse("bars")
        if self.num_of_bars is None:
            raise ValueError("config number of bars parameter in config file and restart app")

        self.max_value = self._config_parse("ascii_max_range")
        if self.max_value is None:
            raise ValueError("config ascii_max_range parameter in config file and restart app")

        # start cava
        self.start_cava()
        # input changed listener start
        self._auto_change_audio_input()

        # volume autosens
        self.min_volume = -1
        self.max_volume = -1
        self._autosens_volume()

    def start_cava(self):
        # start cava with buffer for 1 line
        self._p = Popen([self.cava_command, '-p', self.config_path], stdin=PIPE, stdout=PIPE, stderr=STDOUT, bufsize=1,
                        universal_newlines=True)

    def _autosens_volume(self):
        self.min_volume = -1
        self.max_volume = -1
        print("volume min max recalculated")
        self.thread_autosens_volume = threading.Timer(10, self._autosens_volume)
        self.thread_autosens_volume.start()

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
            for numeric_string in splited[:len(splited) - 1]:
                int_value = int(numeric_string)
                desired_array.append(int_value)
            return desired_array, self._calculate_volume(desired_array)
        return

    def _calculate_volume(self, eq_array):
        # TODO better method to calculate volume
        # volume = 0
        # for i in range(len(eq_array)):
        #     eq_now = eq_array[i]
        #     if i < self.num_of_bars // 3:
        #         volume += eq_now * 0.04
        #     elif self.num_of_bars // 3 <= i < self.num_of_bars // 3 * 2:
        #         volume += eq_now * 0.1
        #     else:
        #         volume += eq_now * 0.08

        volume = sum(eq_array)

        if volume < self.min_volume or self.min_volume == -1:
            self.min_volume = volume
        if volume > self.max_volume or self.max_volume == -1:
            self.max_volume = volume
        if (self.max_volume - self.min_volume) == 0:
            return int(volume)
        return int((volume - self.min_volume) * self.max_value // (self.max_volume - self.min_volume))
        # return sum(eq_array) // self.num_of_bars * 2

    def _config_parse(self, name):
        config = open(self.config_path, 'r')
        # check all lines
        for line in config:
            # comments throw out
            if line[0] == ";" or line[0] == "#" or line[0] == "[" or line[0] == "\n":
                continue
            if name in line:
                # write to output array
                index = line.find("=")
                return int(line[index + 1:])
        return

    def _auto_change_audio_input(self):
        list_proc = Popen(['pactl list short sinks'], stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                          universal_newlines=True, shell=TRUE)
        out, err = list_proc.communicate()
        out = out.split('\n')
        sink_now = ''
        for line in out:
            if "RUNNING" in line:
                sink_now = line.split()[1]
                break
        if sink_now != '':
            if self.sink_name != "" and self.sink_name != sink_now:
                # restart cava if sink changed
                self.kill_cava()
                self.start_cava()
                # recalculate volume
                self.min_volume = -1
                self.max_volume = -1

            self.sink_name = sink_now
        # start new thread
        self.thread_auto_change = threading.Timer(1, self._auto_change_audio_input)
        self.thread_auto_change.start()

    def __del__(self):
        print("cava class destroyed")
        self.kill_cava()
        try:
            self.thread_auto_change.cancel()
        except AttributeError:
            print("thread already killed")
        try:
            self.thread_autosens_volume.cancel()
        except AttributeError:
            print("thread already killed")


class Drawer:
    def __init__(self, num_of_bars, max_value, width=800, height=600, show_volume=False, execute_on_close=None):
        self.width = width
        self.height = height
        # tkinter init
        # window make
        self.root = Tk()
        # Name window
        self.root.title("Cava vis")
        # make Canvas, background black
        self._c = Canvas(self.root, width=width, height=height, bg="Black")
        self._c.grid()
        # focus on canvas to keypress get
        self._c.focus_set()
        # prepare for close
        self._prepare_for_close(execute_on_close)
        # array for bars
        self._bars = []
        # max value
        self.max_value = max_value
        # bars prepare
        # BUG: canvas geometry on start always 1 1, cant calculate correct cords
        for _ in range(num_of_bars):
            self._bars.append(self._c.create_rectangle(0, 0, 0, 0, fill="White"))
        self._volume_bar = None
        if show_volume:
            self._volume_bar = self._c.create_rectangle(0, 0, 0, 0, fill="Red")
        # buttons
        self.button_connect = None

    def control_prepare(self, connect=None, effect_change=None):
        self.root.configure(background="#3b3b3b")
        f1 = Frame(self.root, background="#3b3b3b", height=self.height)
        f1.grid(row=0, column=1, sticky="ewns")
        self.button_connect = Button(f1, text="Disconnect", bg="#9aff36", fg="black",
                                     command=lambda: connect(self.change_status_connect), bd=0,
                                     activebackground="#c7ff8f", relief="flat")
        self.button_connect.pack(side="top", pady=2)
        Button(f1, text="Effect0", bg="#ffdd61", fg="black", command=lambda: effect_change(0), bd=0,
               activebackground="#ffe894",
               relief="flat").pack(side="top", pady=2)
        Button(f1, text="Effect1", bg="#ffdd61", fg="black", command=lambda: effect_change(1), bd=0,
               activebackground="#ffe894",
               relief="flat").pack(side="top", pady=2)
        # Button(f1, text="Disconnect", bg="#ff3d3d", fg="black", command=disconnect, bd=0, activebackground="#ff7a7a",
        #      relief="flat").pack(side="bottom", pady=2)
        # button1 = Button(f1, text="QUIT", bg="#ff3d3d", fg="black", command=quit, bd=0, activebackground="#ff7a7a",
        #                  relief="flat").pack(side="top", pady=2)

    def change_status_connect(self, connected):
        print("on change status", connected)
        if self.button_connect is None:
            print("self.button_connect is None")
            return
        if connected:
            self.button_connect.configure(text="Disconnect", bg="#9aff36", fg="black", activebackground="#c7ff8f")
        else:
            self.button_connect.configure(text="Connect", bg="#ff3d3d", fg="black", activebackground="#ff7a7a")

    def change_effect_num(self, status):
        pass

    def change_sleep_mode(self, sleep):
        pass

    def set_values(self, values, volume=None):
        """
        Method that get values and volume and draw proportional bars in display
        :param values: equalizer values
        :param volume: calculated volume(optional)
        :return: Nothing
        """
        w, h = self._get_c_geometry()
        num_of_eg_bars = len(self._bars)
        for i in range(num_of_eg_bars):
            x1, x2 = self._get_bars_x(i, num_of_eg_bars)
            self._c.coords(self._bars[i], x1, h - self._map_value(values[i], 0, self.max_value, 0, h), x2, h)

        if self._volume_bar is not None:
            x1, x2 = self._get_bars_x(num_of_eg_bars, num_of_eg_bars)
            self._c.coords(self._volume_bar, x1, h - self._map_value(volume, 0, self.max_value, 0, h), x2, h)

    def _get_bars_x(self, i, num_of_bars):
        w, h = self._get_c_geometry()
        if self._volume_bar is not None:
            num_of_bars += 1
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


class OutputLed:
    def __init__(self, vid, pid, speed, max_value):
        port_addr = None
        self.connected = True
        self.max_value = max_value
        self.effect = 1
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if hex(port.vid)[2:] == vid and hex(port.pid)[2:] == pid:
                print(port.device)
                port_addr = port.device
                break
        if port_addr is None:
            print("connect led device")
        try:
            self.port = serial.Serial(port_addr, speed)
        except Exception as e:
            print(e)

    def set_values(self, values, volume):
        if self.effect == 0:
            for i in range(len(values)):
                values[i] = self.constrain_value(values[i])
            self.write_in_port(bytearray(values + [10]))
            # print(bytearray(values + [10]))
        if self.effect == 1:
            self.write_in_port(bytearray([self.constrain_value(volume)]))
            # print(self.constrain_value(volume))

    def set_effect(self, num_of_effect):
        if self.write_in_port(bytearray([11] + [num_of_effect])):
            self.effect = num_of_effect

    def constrain_value(self, val):
        # 10 and 11 reserved bytes
        val = val * 255 // self.max_value
        if val > 255:
            val = 255
        if val == 10:
            val = 12
        if val == 11:
            val = 12
        return val

    def write_in_port(self, bytes_array):
        if self.port.is_open:
            try:
                self.port.write(bytes_array)
                return True
            except Exception as e:
                print(e)
        return False

    def connect(self, change_status_func):
        if self.port.is_open:
            self.port.close()
        else:
            self.port.open()
        change_status_func(self.port.is_open)

    def __del__(self):
        self.port.close()


cava = CavaListener(config_path='config_raw', cava_command='./cava/cava')
drawer = Drawer(num_of_bars=cava.num_of_bars, max_value=cava.max_value, show_volume=True, execute_on_close=cava.__del__)
leds = OutputLed(vid="1a86", pid="7523", speed=500000, max_value=cava.max_value)
drawer.control_prepare(connect=leds.connect, effect_change=leds.set_effect)


def main():
    cava_result = cava.process()
    if cava_result is not None:
        values, volume = cava_result
        drawer.set_values(values, volume)
        leds.set_values(values, volume)
        # leds.set_volume(volume // 4)
    drawer.root.after(10, main)


main()
drawer.root.mainloop()
