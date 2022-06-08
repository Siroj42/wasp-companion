import subprocess
import threading
import pexpect
import time
import json
import asyncio
from pynus import tealblue
from bleak import BleakClient
import re

UART_TX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e" #Nordic NUS characteristic for TX
UART_RX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e" #Nordic NUS characteristic for RX

class Event_ts(asyncio.Event):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

    def set(self):
        self._loop.call_soon_threadsafe(super().set)

    def clear(self):
        self._loop.call_soon_threadsafe(super().clear)

class MainThread(threading.Thread):
    def __init__(self, app_object, no_rtc=False, last_command=None, device_mac=None):
        global app
        threading.Thread.__init__(self)
        app = app_object
        self.no_rtc = no_rtc
        self.last_data = None
        self.line = ""
        self.expecting_return = 0
        self.command_return_event = threading.Event()
        self.command_return = None
        self.device_mac = device_mac
        self.last_command = last_command

    def run(self):
        if not self.no_rtc:
            #rtc(self.device_mac)
            print("finished syncing time! connecting to REPL...")
            app.set_syncing(False, desc="Done!")
        else:
            app.set_syncing(False, desc="Done!")
        asyncio.run(self.main())

    def notification_handler(self, sender, data):
        if not (self.last_data == bytes(data).decode('utf-8') and self.last_data == "\n"):
            if bytes(data).decode('utf-8') == "\r" or bytes(data).decode('utf-8') == "\r\n":
                result = re.match('\n{"t":"\w+", "n":"\w+"} +', self.line)
                if result:
                    result_dict = json.loads(self.line)
                    if result_dict["t"] == "music":
                        app.threadP.process_watchcmd(result_dict["n"])
                if self.expecting_return == 1:
                    self.command_return = self.line
                    self.command_return_event.set()
                if self.expecting_return > 0:
                    self.expecting_return -= 1
                self.line = ""
            else:
                self.line = self.line + bytes(data).decode('utf-8')
        self.last_data = bytes(data).decode('utf-8')

    async def main(self):
        self.command_event = Event_ts()
        self.kill_event = Event_ts()
        self.loop = asyncio.get_event_loop()

        if self.last_command:
            self.cmd = self.last_command
            self.command_event.set()

        async with BleakClient(self.device_mac, loop=self.loop) as client:
            self.client = client
            while not client.is_connected:
                asyncio.sleep(0.1)
            await client.start_notify(UART_RX_UUID, self.notification_handler)

            app.threadP.waspconn_ready_event.set()
            app.threadN.waspconn_ready_event.set()
            print("Connection is ready!")

            while True:
                await asyncio.wait([self.command_event.wait(), self.kill_event.wait()], return_when=asyncio.FIRST_COMPLETED)
                if self.command_event.is_set():
                    self.command_event.clear()
                    for char in self.cmd:
                        await self.client.write_gatt_char(UART_TX_UUID, bytearray(bytes(char, 'utf-8')))
                elif self.kill_event.is_set():
                    print("threadW is being killed!")
                    await self.client.disconnect()
                    break

    def run_command(self, cmd, expect_return=False):
        self.cmd = cmd + "\r"
        self.last_command = self.cmd
        if expect_return:
            self.expecting_return = 2
        self.command_event.set()
        if expect_return:
            self.command_return_event.wait()
            self.command_return_event.clear()
            return self.command_return

class ReconnectThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.reconnect_event = threading.Event()
		self.kill_event = threading.Event()

	def run(self):
		while not self.kill_event.is_set():
			self.reconnect_event.wait(timeout=1)
			if self.reconnect_event.is_set():
				last_command = app.threadW.last_command
				app.set_syncing(False, "Lost connection!")
				app.threadW.kill_event.set()
				for i in range(self.countdown):
					app.set_syncing(False, "Retrying in " + str(10-i) + " seconds")
					time.sleep(1)
				app.threadW = MainThread(app, no_rtc=True, last_command=last_command, device_mac="E9:83:D7:36:3D:0E") #TODO: Need to get device_mac from database or sth.
				app.threadW.start()
				self.reconnect_event.clear()

	def reconnect(self, countdown=0):
		self.countdown = countdown
		self.reconnect_event.set()

class ScanThread(threading.Thread):
	def __init__(self, app):
		threading.Thread.__init__(self)
		self.kill_event = threading.Event()
		self.app = app
	def run(self):
		WASP_NUS_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
		DFU_SERVICE_UUID = '00001530-1212-efde-1523-785feabcd123'
		adapter = tealblue.TealBlue().find_adapter()
		with adapter.scan() as scanner:
			for device in scanner:
				if self.kill_event.is_set():
					return
				if WASP_NUS_SERVICE_UUID in device.UUIDs:
					self.app.on_device_scanned(device.name, device.address)
				elif DFU_SERVICE_UUID in device.UUIDs:
					if device.name.startswith("InfiniTime") or device.name.startswith("Pinetime-JF") or device.name.startswith("PineTime") or device.name.startswith("Y7S"):
						self.app.on_device_scanned(device.name, device.address, type="infinitime")
					elif device.name.startswith("PineDFU"):
						self.app.on_device_scanned(device.name, device.address, type="dfu")

def rtc(device_mac):
	app.set_syncing(True)
	output=subprocess.check_output(['/app/bin/wasptool','--check-rtc', '--device=' + device_mac],universal_newlines=True)
	if output.find("delta 0") >= 0:
		print("time is already synced")
	else:
		app.set_syncing(True, desc="Syncing time...")
		output=subprocess.check_output(['/app/bin/wasptool','--rtc', '--device=' + device_mac],universal_newlines=True)
		print(output)
	app.set_syncing(False, desc="Done!")
