import threading
import time
import json
import asyncio
import janus
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from logic import *
import re
import logging

import os
LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
logging.basicConfig(level=LOGLEVEL)

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
	def __init__(self, app_object, no_rtc=False, device_mac=None):
		threading.Thread.__init__(self)
		self.app = app_object
		self.no_rtc = no_rtc
		self.last_data = None
		self.line = ""
		self.expecting_return = 0
		self.command_return_event = threading.Event()
		self.waspconn_ready_event = threading.Event()
		self.command_return = None
		self.device_mac = device_mac
		self.last_command = None

	def run(self):
		asyncio.run(self.main())

	def notification_handler(self, sender, data):
		logging.info("Handling notification...")
		if not (self.last_data == bytes(data).decode('utf-8') and self.last_data == "\n"):
			if bytes(data).decode('utf-8').startswith(">>>") and self.expecting_return > 0:
				self.expecting_return = 0
				self.return_queue.sync_q.put(self.return_value)
			if bytes(data).decode('utf-8') == "\r" or bytes(data).decode('utf-8') == "\r\n":
				result = re.match('\n{"t":"\w+", "n":"\w+"} +', self.line)
				if result:
					result_dict = json.loads(self.line)
					if result_dict["t"] == "music":
						try:
							self.app.threadP.process_watchcmd(result_dict["n"])
						except:
							logging.error("Problem occured while trying to process watch command")
				if self.expecting_return == 2:
					self.return_value = []
					self.expecting_return = 1
				elif self.expecting_return == 1:
					self.return_value.append(self.line)
				logging.info("Received line '{}'".format(self.line))
				self.line = ""
			else:
				self.line = self.line + bytes(data).decode('utf-8')
		self.last_data = bytes(data).decode('utf-8')

	async def main(self):
		self.cmd_queue = janus.Queue()
		self.return_queue = janus.Queue()
		self.command_event = Event_ts()
		self.reconnect_event = Event_ts()
		self.kill_event = Event_ts()
		self.command_done_event = Event_ts()
		self.command_done_event.set()
		self.loop = asyncio.get_event_loop()

		self.app.set_syncing(True, "Connecting...")
		while True:
			try:
				async with BleakClient(self.device_mac, loop=self.loop) as client:
					logging.info("Client created")
					self.client = client
					#while not client.is_connected:
					#	await asyncio.sleep(0.1)
					logging.info("Client is connected")
					self.app.set_syncing(False, "Done!")

					service_collection = await client.get_services()
					for c in service_collection.characteristics:
						desc = service_collection.characteristics[c].description
						if desc == "Nordic UART TX":
							tx = service_collection.characteristics[c]
						elif desc == "Nordic UART RX":
							rx = service_collection.characteristics[c]

					await client.start_notify(tx, self.notification_handler)
					logging.info("Started notifications")

					if self.last_command:
						self.command_done_event.clear()
						for char in self.last_command:
							try:
								await self.client.write_gatt_char(rx, bytearray(bytes(char, 'utf-8')))
							except BleakError:
								self.command_event.set()
								self.reconnect(countdown=5)
						self.last_command = None
						if self.expecting_return > 0:
							await self.command_done_event.wait()

					self.waspconn_ready_event.set()

					while not self.reconnect_event.is_set():
						await asyncio.wait([self.command_event.wait(), self.kill_event.wait(), self.reconnect_event.wait()], return_when=asyncio.FIRST_COMPLETED)
						if self.command_event.is_set() and not self.reconnect_event.is_set():
							self.command_event.clear()
							self.command_done_event.clear()
							command = await self.cmd_queue.async_q.get()
							logging.info("Received command")
							try:
								for char in command:
									await self.client.write_gatt_char(rx, bytearray(bytes(char, 'utf-8')))
								logging.info("Done writing command, waiting until return")
								if self.expecting_return > 0:
									await self.command_done_event.wait()
							except BleakError:
								logging.warning("Failed to write, reconnecting in 5 seconds")
								self.last_command = command
								r = threading.Thread(target=self.reconnect)
								r.run()
							self.cmd_queue.async_q.task_done()
						elif self.kill_event.is_set():
							await self.client.disconnect()
							return
					await self.on_reconnect()
					await self.client.disconnect()
			except BleakError:
				logging.warning("Connection failed, retrying in 10 seconds")
				self.reconnect_countdown = 10
				await self.on_reconnect()

	def rtc(self):
		logging.info("Starting RTC check")
		self.app.set_syncing(True)
		result = self.run_command('print(watch.rtc.get_localtime())', expect_return=True)[0]
		time_check = re.match('\(([0-9]+), ([0-9]+), ([0-9]+), ([0-9]+), ([0-9]+), ([0-9]+), ([0-9]+), ([0-9]+)\)', result)
		t = time.localtime()

		watch_hms = (int(time_check[4]), int(time_check[5]), int(time_check[6]))
		watch_str = f'{watch_hms[0]:02d}:{watch_hms[1]:02d}:{watch_hms[2]:02d}'
		host_hms = (t.tm_hour, t.tm_min, t.tm_sec)
		host_str = f'{host_hms[0]:02d}:{host_hms[1]:02d}:{host_hms[2]:02d}'
		delta = 3600 * (host_hms[0] - watch_hms[0]) + \
						60 * (host_hms[1] - watch_hms[1]) + \
						(host_hms[2] - watch_hms[2])

		if delta != 0:
			logging.info("There is a RTC deviation, starting time sync")
			self.app.set_syncing(True, desc="Syncing time...")
			now = then = time.localtime()
			while now[5] == then[5]:
				now = time.localtime()

			self.run_command(f'watch.rtc.set_localtime(({now[0]}, {now[1]}, {now[2]}, {now[3]}, {now[4]}, {now[5]}, {now[6]}, {now[7]}))')

		logging.info("RTC is done")
		self.app.set_syncing(False, desc="Done!")

	def run_command(self, cmd, expect_return=False):
		logging.info("Running command {}".format(cmd))
		self.cmd_queue.sync_q.join()
		self.cmd_queue.sync_q.put(cmd + "\r")
		logging.info("Added command to queue")
		self.expecting_return = 2
		self.command_event.set()
		logging.info("Waiting for return value")
		r = self.return_queue.sync_q.get()
		self.return_queue.sync_q.task_done()
		self.command_done_event.set()
		logging.info("command '{}' done".format(cmd))
		if expect_return:
			return r

	def reconnect(self, countdown=5):
		self.reconnect_countdown = countdown
		self.reconnect_event.set()

	async def on_reconnect(self):
		logging.info("Reconnect invoked")
		for i in range(0, self.reconnect_countdown):
			self.app.set_syncing(True, "Reconnecting in {} seconds".format(self.reconnect_countdown-i))
			await asyncio.sleep(1)
		self.app.set_syncing(True, "Reconnecting...")
		self.reconnect_event.clear()

class ScanThread(threading.Thread):
	def __init__(self, app):
		threading.Thread.__init__(self)
		self.app = app
	def run(self):
		asyncio.run(self.scan())

	async def scan(self):
		WASP_NUS_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
		DFU_SERVICE_UUID = '00001530-1212-efde-1523-785feabcd123'

		logging.info("Scanning for bluetooth devices")
		devices = await BleakScanner.discover()
		logging.info("Scan done")
		for device in devices:
			if WASP_NUS_SERVICE_UUID in device.metadata["uuids"]:
				self.app.on_device_scanned(device.name, device.address)
			elif DFU_SERVICE_UUID in device.metadata["uuids"]:
					if device.name.startswith("InfiniTime") or device.name.startswith("Pinetime-JF") or device.name.startswith("PineTime") or device.name.startswith("Y7S"):
						self.app.on_device_scanned(device.name, device.address, software=DeviceSoftware.INFINITIME)
					elif device.name.startswith("PineDFU"):
						self.app.on_device_scanned(device.name, device.address, software=DeviceSoftware.DFU)
