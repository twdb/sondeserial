# Author: Taylor Sansom (taylor.sansom@twdb.texas.gov)
# Created: 2/1/2018

'''
This is a small piece of a larger project to create a (near) real-time
monitoring system for instruments deployed in the bays and estuaries along the
Texas coast using a novel raspberry pi setup. The objective of this package
is to create a simple interface between the raspberry pi and the sonde.
'''

import serial
from serial.tools.list_ports import comports
from time import sleep


class YSI600:
    '''
    Create and manipulate a serial connection to a YSI 600 sonde.
    '''
    def __init__(self, port=None, timeout=5, baudrate=None):
        '''
        Initialize the attributes
        '''
        self.port = port
        self.ser = None
        self.timeout = timeout
        self.sn = None
        self.status = {}
        self.files = {}
        self.report = {}
        self.connected = False
        self.log_head = None

        self.ser = serial.Serial()  # create the connection
        self.get_port()
        self.ser.port = self.port
        self.ser.timeout = self.timeout
        self.connect()  # connect
        # self.get_sn()
        # self.get_status()
        # self.get_files()
        # self.get_report()

    def get_port(self):
        '''
        If port is passed in, test the connection. If not, figure out which
        port has the serial connection.
        '''
        print('Getting port... ', end='')
        if self.port is not None:  # if a port is given
            try:
                sleep(0.2)
                ser = serial.Serial(self.port)
                sleep(0.2)
                ser.write(b'0')
                sleep(0.1)
                assert ser.in_waiting > 0, 'no serial connection on port {}'\
                    .format(self.port)
                ser.close()
            except serial.SerialException:
                raise
            except AssertionError:
                ser.close()
                raise
        else:  # if no port is given
            for comport in [cp.device for cp in comports()]:
                try:
                    ser = serial.Serial(comport)
                    sleep(0.2)
                    ser.write(b'0')
                    sleep(0.2)
                    assert ser.in_waiting > 0
                    self.port = comport
                    ser.close()
                    break
                except:
                    ser.close()
        print('{}'.format(self.port))

    def connect(self):
        '''
        Open the serial connection (if it's not open already)
        '''
        sleep(0.1)
        if not self.ser.is_open:
            self.ser.open()
        self.connected = True

    def disconnect(self):
        '''
        Close the serial connection (if it's not already closed)
        '''
        if self.ser.is_open:
            self.ser.close()
        self.connected = False
        sleep(0.1)

    def flush_all(self):
        '''
        Flush the inputs and outputs so nothing is in the buffer
        '''
        sleep(0.2)
        self.ser.flushInput()
        self.ser.flushOutput()

    def write(self, s):
        '''
        Write something (s) to the sonde in order to navigate menu or change
        menu options. Serial connections via pyserial only accept bytes, but
        this method will convert strings or integers to bytes before writing
        to the sonde.
        '''
        if isinstance(s, str):
            self.ser.write(s.encode())
        elif isinstance(s, int):
            self.ser.write(str(s).encode())
        elif isinstance(s, bytes):
            self.ser.write(s)
        else:
            raise TypeError('cannot write data of type {} - only string, bytes'
                            'or integer')
        sleep(0.2)

    def main_menu(self):
        '''
        This will return the connection to the main menu.
        '''
        self.flush_all()
        self.write(0)
        # if it's at the command prompt, get to menu
        if self.ser.in_waiting == 1:
            self.write('\r\nmenu\r\n')
        # if in the menu, make sure you are in the top menu (Main)
        else:
            for _ in range(4):
                self.write(0)
            sleep(0.1)
            self.write('n')
        sleep(0.1)
        self.flush_all()

    def read_all(self):
        '''
        Read data in the buffer if there is any.
        '''
        if self.ser.in_waiting > 0:
            lines = [line.rstrip()
                         .decode()
                         .replace('\x1b[2J\x1b[1;1H', '')
                         .replace('\x08', '')
                     for line in self.ser.readlines()]
        # make sure there is nothing in the buffer - might need to append
        # data or change sleep timing if so
        assert self.ser.in_waiting == 0
        return lines

    def get_sn(self):
        '''
        Retrieve the sonde's serial number
        '''
        print('Getting serial number... ', end='')
        self.main_menu()
        self.write(5)
        sleep(0.1)
        self.sn = \
            [x.split('=')[-1] for x in self.read_all()
                if 'Instrument ID' in x][0]
        print('{}'.format(self.sn))

    def get_status(self):
        '''
        Retrieve all status entries
        '''
        print('Getting status... ', end='')
        self.main_menu()
        self.write(4)
        for line in self.read_all():
            if 'Date' in line:
                self.status['date'] = line.split('=')[-1]
            if 'Time' in line:
                self.status['time'] = line.split('=')[-1]
            if 'Bat volts' in line:
                self.status['battery_volts'] = line.split(': ')[-1]
            if 'Bat life' in line:
                self.status['battery_life'] = ' '.join(line.split()[-2:])
            if 'Free bytes' in line:
                self.status['free_bytes'] = line.split(':')[-1]
            if 'Logging' in line:
                self.status['logging'] = line.split(':')[-1]
        print('Done')

    def get_files(self):
        '''
        Retrieve all files and file sizes in the sonde's memory.
        '''
        print('Getting files... ', end='')
        self.main_menu()
        # the file list is in a third tier menu, discard first menu buffer
        self.write(3)
        self.flush_all()
        # now get to the files submenu
        self.write(1)
        for line in self.read_all():
            if len(line) > 1:
                if line[1] == '-':
                    self.files[line.split()[0][2:]] = line.split()[-1]
        print('Done')

    def get_report(self):
        '''
        Retrive all report variables
        '''
        print('Getting all report variables... ', end='')
        self.main_menu()
        self.write(6)
        tmp = []
        for line in self.read_all():
            if '( )' in line or '(*)' in line:
                if len(line) > 20:
                    tmp.append(line[2:20].rstrip())
                    tmp.append(line[22:].rstrip())
                else:
                    tmp.append(line[2:].rstrip())
        for v in tmp:
            if v[1] == '*':
                self.report[v[3:]] = True
            else:
                self.report[v[3:]] = False
        print('Done')

    def log_sample(self):
        '''
        Save a discrete sample
        '''
        print('Logging a discrete sample (~20 seconds)... ', end='')
        self.main_menu()
        self.write(1)
        self.write(1)
        self.flush_all()
        self.write(1)
        sleep(8)
        self.write(0)
        log = self.read_all()
        print('Done')
        if self.log_head is None:
            self.log_head = log[2]
        for line in log[6:]:
            if line[:4] == '2018':
                return line
        else:
            return 'no data logged - check sample interval'
