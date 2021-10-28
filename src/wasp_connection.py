import subprocess
import threading
import pexpect
import time
import json

expect_command = 'print(">>>>", {cmd})'

class MainThread(threading.Thread):
	def __init__(self, app_object, no_rtc=False, last_command=None):
		global app
		threading.Thread.__init__(self)
		app = app_object
		self.last_command = None
		self.running = True
		self.command_return = None
		self.command_to_run = None
		self.last_command = last_command
		self.no_rtc = no_rtc
		self.kill_event = threading.Event()
		self.command_done_event = threading.Event()

	def run(self):
		print("starting wasptool thread...")

		if not self.no_rtc:
			rtc()
			print("finished syncing time! connecting to REPL...")
		else:
			app.set_syncing(False, desc="Done!")

		self.c = pexpect.spawn('./wasptool --console', encoding='UTF-8')
		self.c.expect('Connect.*\(([0-9A-F:]*)\)')
		self.c.expect('Exit console using Ctrl-X')
		print("connected to REPL!")

		self.commandThread = CommandThread(self)
		self.commandThread.start()

		app.threadP.waspconn_ready_event.set()

		while not self.kill_event.is_set():
			try:
				self.c.expect('{"t":"\w+", "n":"\w+"}', timeout=0.1)
				output = json.loads(self.c.match.group())
				if output["t"] == "music":
					app.threadP.process_watchcmd(output["n"])
			except:
				self.commandThread.command_clear_event.set()
				self.command_done_event.wait()
				self.command_done_event.clear()

		app.threadW.commandThread.kill_event.set()
		print("Quitting console...")
		self.c.sendcontrol('x')
		self.running = False

	def run_command(self, cmd, expect_return=False):
		print("Running command...")
		self.command_to_run = cmd
		self.commandThread.expect_return = expect_return
		if expect_return:
			self.command_return = None
		self.commandThread.run_command_event.set()
		time.sleep(0.05)
		self.command_done_event.wait()
		if expect_return:
			return self.command_return

class CommandThread(threading.Thread):
	def __init__(self, parent):
		threading.Thread.__init__(self)
		self.run_command_event = threading.Event()
		self.kill_event = threading.Event()
		self.command_clear_event = threading.Event()
		self.c = parent.c
		self.parent = parent
		self.expect_return = False

	def run(self):
		if self.parent.last_command:
			self.run_command_event.set()
			self.parent.command_to_run = self.parent.last_command
			self.parent.last_command = None
		while not self.kill_event.is_set():
			if self.run_command_event.is_set():
				self.command_clear_event.wait()
				try:
					if self.expect_return:
						self.c.sendline(self.parent.command_to_run)
						self.c.expect(self.parent.command_to_run)
						self.c.expect('\n')
						self.c.expect('\w+', timeout=1)
						self.parent.command_return = self.c.match.group()
					else:
						self.c.sendline(self.parent.command_to_run)
					self.c.expect('>>> ')
				except:
					self.parent.last_command = self.parent.command_to_run
					app.threadR.reconnect_event.set()
				self.run_command_event.clear()
			self.parent.command_done_event.set()
			self.command_clear_event.clear()

class ReconnectThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.reconnect_event = threading.Event()
		self.kill_event = threading.Event()
	def run(self):
		while not self.kill_event.is_set():
			if self.reconnect_event.is_set():
				last_command = app.threadW.last_command
				app.set_syncing(False, "Lost connection!")
				app.threadW.kill_event.set()
				for i in range(10):
					app.set_syncing(False, "Retrying in " + str(10-i) + " seconds")
					time.sleep(1)
				app.threadW = MainThread(app, no_rtc=True, last_command=last_command)
				app.threadW.start()
				self.reconnect_event.clear()

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
