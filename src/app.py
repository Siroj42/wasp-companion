import os
import subprocess
import sys
import gi
import threading
import pexpect
import wasp_connection
import media_player
import json
from pathlib import Path
import notifications

# UI library
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
# Mobile GTK widgets
gi.require_version('Handy','1')
from gi.repository import Handy
# Music player control
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib
# Gio
from gi.repository import Gio

# return true to prevent other signal handlers from deleting objects from the builder
class Handler:
	def _btnClose(self, *args):
		# destroy window
		app.window.destroy()
		# set app.window to none, prompting window re-creation on next activation
		app.window = None
		return True

	def _btnQuit(self, *args):
		# release app (stop keeping it alive)
		app.release()
		# properly quit the app
		app.quit()
		# exit all threads
		os._exit(1)

	def _btnAbout(self, *args):
		o("windowAbout").show()
		return True
	
	def _closeAbout(self, *args):
		o("windowAbout").hide()
		return True

	def _btnReconnect(self, *args):
		app.threadW.reconnect()
		return True

class Companion(Gtk.Application):
	def __init__(self):
		Gtk.Application.__init__(self,
			application_id="com.arteeh.Companion",
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
		Gtk.Application.quit(self)

	def do_startup(self):
		Gtk.Application.do_startup(self)
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
		self.device_selector_window.close()

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
			self.o("spnInitializing").start()
		else:
			self.o("spnInitializing").stop()
		self.o("lblInitializing").set_label(desc)
		self.sync_desc_str = desc
		self.sync_activity = active

	def create_window(self):
		Gtk.init()
		Handy.init()
		global builder
		builder = Gtk.Builder()
		builder.add_from_file("/app/bin/app.ui")
		builder.connect_signals(Handler())
		self.objects = builder.get_objects()
		self.window = self.o("window")
		self.window.set_application(self)
		self.device_selector_window = self.o("device_selector_window")
		self.device_selector_window.set_transient_for(self.window)

		if not self.in_startup:
			# skip in startup because sync_activity and sync_desc_str are not available yet
			self.set_syncing(self.sync_activity, self.sync_desc_str)

		self.window.show_all()

	def select_device(self):
		self.device_selector_window.show_all()

		self.threadS = wasp_connection.ScanThread(self)
		self.threadS.start()

	def on_device_scanned(self, name, address, type="nus", version="0"):
		if address == self.config["last_device"]:
			self.connect(None, address)
			return
		devrow = Handy.ActionRow()
		devrow.set_title(name)
		devrow.set_activatable_widget(devrow)
		devrow.set_activatable_widget(None)
		if type=="nus":
			devrow.set_subtitle("Wasp-OS")
			devrow.connect("activated", self.connect, address)
		elif type=="infinitime":
			devrow.set_subtitle("InfiniTime")
			devrow.connect("activated", print, "There currently is no way to connect to InfiniTime devices")
		elif type=="dfu":
			devrow.set_subtitle("Wasp-OS (Bootloader)")
			devrow.connect("activated", print, "There currently is no way to connect to the Wasp-OS Bootloader")

		self.o("device_selector_device_list").insert(devrow, 0)
		devrow.show()

	def o(self, name):
		for i in range(0, len(self.objects)):
			if self.objects[i].get_name() == name:
				return self.objects[i]
		return -1

# Fuction for grabbing UI objects
def o(name):
	for i in range(0,len(app.objects)):
		if app.objects[i].get_name() == name:
			return app.objects[i]
	return -1

if __name__ == "__main__":
	global app
	app = Companion()
	app.run(sys.argv)

