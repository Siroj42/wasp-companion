import os
import subprocess
import sys
import gi
import threading
import pexpect
import wasp_connection
from logic import *
import media_player
import json
from ui import *
from pathlib import Path
import notifications

#TODO: Finish GTK4 Port:
#	1. [x] Find out why window contents do not render
#	2. [x] Stop relying on app.objects
#	3. [x] Reimplement signals handling
#	4. [x] Port to Adw.Application
#	5. [x] Refactor (maybe into different files?)
#	6. [ ] UI updates
#	  - [ ] Access Device Selector during normal operation
#	  - [ ] Device overview page with reconnect & disconnect button
#	7. [ ] Translations (start with German)

# Mobile GTK widgets
gi.require_version('Adw','1')
from gi.repository import Adw
# Music player control
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib, GObject
# Gio
from gi.repository import Gio

class Companion(Adw.Application):
	def __init__(self):
		Adw.Application.__init__(self,
			application_id="io.github.siroj42.WaspCompanion",
			flags=Gio.ApplicationFlags.FLAGS_NONE)
		self.window = None

	def quit(self):
		config_path = Path(GLib.get_user_config_dir() + "/wasp-companion.json")
		with open(config_path, "w") as f:
			json.dump(self.config, f)
		try:
			self.threadW.kill_event.set()
		except:
			print("threadW is not running yet")
		try:
			self.threadP.quit()
		except:
			print("threadP is not running yet")
		try:
			self.threadN.quit()
		except:
			print("threadN is not running yet")
		try:
			self.threadW.join()
		except:
			print("threadW is not running yet")
		Adw.Application.quit(self)

	def do_startup(self):
		Adw.Application.do_startup(self)
		self.hold()

		self.in_startup = True
		# declare that the application is currently starting up. Certain variables are not available yet.

		config_path = Path(GLib.get_user_config_dir() + "/wasp-companion.json")
		if config_path.is_file():
			with open(config_path, "r") as f:
				self.config = json.load(f)
		else:
			self.config = {"version": 1, "last_device": ""}
			with open(config_path, "w+") as f:
				json.dump(self.config, f)

		self.create_window()
		self.select_device()

	def connect(self, action_row, device_mac):
		print("connecting...")
		self.window.device_selector_window.close()

		self.config["last_device"] = device_mac

		self.threadW = wasp_connection.MainThread(self, device_mac=device_mac)
		self.threadP = media_player.MainThread(self)
		self.threadN = notifications.MainThread(self)

		self.threadW.start()
		self.threadP.start()
		self.threadN.start()

		self.threadW.waspconn_ready_event.wait()
		self.threadW.rtc()

		self.in_startup = False

	def do_activate(self):
		if not self.window:
			self.create_window()
		self.window.present()

# change the parts of the UI relevant to syncing: Sync spinner and sync label.
	def set_syncing(self, active, desc="Checking if time is synced..."):
		if active:
			self.window.spnInitializing.start()
		else:
			self.window.spnInitializing.stop()
		self.window.lblInitializing.set_label(desc)
		self.sync_desc_str = desc
		self.sync_activity = active

	def create_window(self):
		Adw.init()

		self.window = MainWindow(self)
		self.window.set_application(self)
		self.window.device_manager_button_clicked()

		if not self.in_startup:
			# skip in startup because sync_activity and sync_desc_str are not available yet
			self.set_syncing(self.sync_activity, self.sync_desc_str)

	def select_device(self):
		print("Starting scan thread...")
		self.threadS = wasp_connection.ScanThread(self)
		self.threadS.start()

	def on_device_scanned(self, name, address, software=DeviceSoftware.WASP, version="0"):
		self.window.device_selector_window.add_row(name, software, DeviceType.PINETIME, self.connect, address)

	@GObject.Signal
	def button_close(self):
		print("Closing window...")
		self.destroy()
		self.app.window = None

if __name__ == "__main__":
	global app
	app = Companion()
	app.run(sys.argv)

