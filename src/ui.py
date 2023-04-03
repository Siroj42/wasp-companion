from logic import DeviceSoftware, DeviceType
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw','1')

from gi.repository import Gtk, Adw, Gdk

theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
theme.add_search_path("/app/data/icons")

@Gtk.Template(filename="/app/data/ui/window.ui")
class MainWindow(Adw.ApplicationWindow):
	__gtype_name__ = "MainWindow"

	spnInitializing = Gtk.Template.Child()
	lblInitializing = Gtk.Template.Child()

	def __init__(self, app, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.app = app

	@Gtk.Template.Callback()
	def close_button_clicked(self, *args):
		self.destroy()
		self.app.window = None

	@Gtk.Template.Callback()
	def reconnect_button_clicked(self, *args):
		self.app.threadW.reconnect()

	@Gtk.Template.Callback()
	def device_manager_button_clicked(self, *args):
		self.app.select_device()
		self.device_selector_window = DeviceSelectorWindow()
		self.device_selector_window.set_transient_for(self)

	@Gtk.Template.Callback()
	def about_button_clicked(self, *args):
		self.about_dialog = Gtk.AboutDialog(transient_for=self, modal=True)
		self.about_dialog.present()

	@Gtk.Template.Callback()
	def quit_button_clicked(self, *args):
		self.app.release()
		self.app.quit()
		os._exit(1)

@Gtk.Template(filename="/app/data/ui/device_selector.ui")
class DeviceSelectorWindow(Adw.Window):
	__gtype_name__ = "DeviceSelectorWindow"

	device_selector_device_list = Gtk.Template.Child()

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.show()

	def add_row(self, device_name, device_software, device_type, connect_method, device_address):
		new_row = DeviceRow(device_name, device_software, device_type, connect_method, device_address)
		self.device_selector_device_list.insert(new_row, 0)

	@Gtk.Template.Callback()
	def on_closed(self, *args):
		self.destroy()
		self = None

class DeviceRow(Adw.ActionRow):
	def __init__(self, device_name, device_software, device_type, connect_method, device_address, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.set_title(device_name)
		if device_software == DeviceSoftware.WASP:
			self.set_subtitle("Wasp-OS")
			self.connect("activated", connect_method, device_address)
		elif device_software == DeviceSoftware.INFINITIME:
			self.set_subtitle("InfiniTime")
			self.connect("activated", print, "There currently is no way to connect to InfiniTime devices")
		elif device_software == DeviceSoftware.DFU:
			self.set_subtitle("Wasp-OS (Bootloader)")
			self.connect("activated", print, "There currently is no way to connect to the Wasp-OS Bootloader")

		self.set_activatable(True)
