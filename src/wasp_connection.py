import subprocess
import threading
import pexpect
import time

command_return = None
command_to_run = None

class MainThread(threading.Thread):
	def __init__(self, app_object):
		global app
		threading.Thread.__init__(self)
		app = app_object
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
		self.expectThread.no_command_event.set()
		self.expectThread.start()
		self.commandThread = commandThread(c, self)
		self.commandThread.start()

		while True:
			self.expect_event.wait()
			print(c.match.group())
			self.check_event.clear()
			self.expectThread.expect_process_event.set()

class expectThread(threading.Thread):
	def __init__(self, c, parent):
		threading.Thread.__init__(self)
		self.no_command_event = threading.Event()
		self.expect_process_event = threading.Event()
		self.c = c
		self.parent = parent

	def run(self):
		while True:
			self.no_command_event.wait()
			self.c.expect('{"t":"\w+", "n":"\w+"}')
			self.parent.expect_event.set()
			self.expect_process_event.wait()
			self.expect_process_event.clear()

class commandThread(threading.Thread):
	def __init__(self, c, parent):
		threading.Thread.__init__(self)
		self.run_command_event = threading.Event()
		self.c = c
		self.parent = parent

	def run(self):
		global command_return
		global command_to_run
		while True:
			self.run_command_event.wait()
			self.parent.expectThread.no_command_event.clear()
			self.c.sendline(command_to_run)
			self.c.expect_exact(command_to_run)
			self.c.expect('>>> ')
			command_return = self.c.before.replace('\r\r\n', '\n').strip('\n')
			self.parent.expectThread.no_command_event.set()
			t2.return_event.set()
			self.run_command_event.clear()

def rtc():
	app.set_syncing(True)
	output=subprocess.check_output(['/app/bin/wasptool','--check-rtc'],universal_newlines=True)
	if output.find("delta 0") >= 0:
		print("time is already synced")
	else:
		app.set_syncing(True, desc="Syncing time...")
		#output=subprocess.check_output(['/app/bin/wasptool','--rtc'],universal_newlines=True)
		print(output)
	app.set_syncing(False, desc="Done!")
