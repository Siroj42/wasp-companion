import subprocess
import threading
import pexpect
import time
import json

class MainThread(threading.Thread):
	def __init__(self, app_object):
		global app
		threading.Thread.__init__(self)
		app = app_object
		self.command_return = None
		self.command_to_run = None
		self.expect_event = threading.Event()

	def run(self):
		print("starting wasptool thread...")
		rtc()
		print("finished syncing time! connecting to REPL...")

		c = pexpect.spawn('./wasptool --console', encoding='UTF-8')
		c.expect('Connect.*\(([0-9A-F:]*)\)')
		c.expect('Exit console using Ctrl-X')
		print("connected to REPL!")

		self.expectThread = expectThread(c, self)
		self.expectThread.start()
		self.commandThread = commandThread(c, self)
		self.commandThread.start()

		app.threadP.waspconn_ready_event.set()

		while True:
			self.expect_event.wait()
			output = json.loads(c.match.group())
			if output["t"] == "music":
				app.threadP.process_watchcmd(output["n"])

			self.expect_event.clear()
			self.expectThread.expect_process_event.set()

	def run_command(self, cmd):
		self.command_to_run = cmd
		self.commandThread.run_command_event.set()

class expectThread(threading.Thread):
	def __init__(self, c, parent):
		threading.Thread.__init__(self)
		self.command_done_event = threading.Event()
		self.expect_process_event = threading.Event()
		self.c = c
		self.parent = parent

	def run(self):
		while True:
			try:
				self.c.expect('{"t":"\w+", "n":"\w+"}', timeout=0.1)
				self.parent.expect_event.set()
				self.expect_process_event.wait()
				self.expect_process_event.clear()
			except:
				self.parent.commandThread.command_clear_event.set()
				self.command_done_event.wait()

class commandThread(threading.Thread):
	def __init__(self, c, parent):
		threading.Thread.__init__(self)
		self.run_command_event = threading.Event()
		self.command_clear_event = threading.Event()
		self.c = c
		self.parent = parent

	def run(self):
		while True:
			try:
				self.run_command_event.wait()
				self.command_clear_event.wait()
				print(self.parent.command_to_run)
				self.c.sendline(self.parent.command_to_run)
				self.c.expect('>>> ')
				self.parent.expectThread.command_done_event.set()
				self.run_command_event.clear()
				self.command_clear_event.clear()
			except:
				pass

def rtc():
	app.set_syncing(True)
	output=subprocess.check_output(['/app/bin/wasptool','--check-rtc'],universal_newlines=True)
	if output.find("delta 0") >= 0:
		print("time is already synced")
	else:
		app.set_syncing(True, desc="Syncing time...")
		output=subprocess.check_output(['/app/bin/wasptool','--rtc'],universal_newlines=True)
		print(output)
	app.set_syncing(False, desc="Done!")
