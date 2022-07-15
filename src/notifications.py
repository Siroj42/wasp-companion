from dbus.mainloop.glib import DBusGMainLoop
import gi
import dbus
import threading

from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

pc_notif_commands = {
	"notify": 'GB({{"t":"notify","id":"{notif_id}","src":"{src}","title":"{title}","body":"{body}"}})',
	"unnotify": 'GB({{"t":"notify-","id":"{notif_id}"}})'
}

class MainThread(threading.Thread):
	def __init__(self, app_object):
		global app
		global thread
		thread = self
		app = app_object
		self.session_bus = dbus.SessionBus()
		self.serials = []
		self.notifs = {}
		threading.Thread.__init__(self)

	def run(self):
		self.notif_dbus = self.session_bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		self.fd_dbus = self.session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
		self.fd_dbus.BecomeMonitor(
			[
				"type='method_return'",
				"type='method_call', interface='org.freedesktop.Notifications', member='Notify'",
				"type='signal', interface='org.freedesktop.Notifications', member='NotificationClosed'"],
			0,
			dbus_interface='org.freedesktop.DBus.Monitoring'
		)
		self.session_bus.add_message_filter(self.on_message)

		self.main = GLib.MainLoop()
		self.main.run()

	def quit(self):
		self.main.quit()

	def on_message(self, bus, message):
		args = message.get_args_list()
		if isinstance(message, dbus.lowlevel.MethodCallMessage):
			src = args[0]
			title = args[3]
			body = args[4]
			for n in self.notifs:
				if self.notifs[n] == {"src": src, "title": title, "body": body}:
					return
			self.notifs[str(message.get_serial())] = {"src": src, "title": title, "body": body}
		elif isinstance(message, dbus.lowlevel.MethodReturnMessage):
			reply_serial = str(message.get_reply_serial())
			if reply_serial in self.notifs:
				notif_id = args[0]
				src = self.notifs[reply_serial]["src"]
				title = self.notifs[reply_serial]["title"]
				body = self.notifs[reply_serial]["body"]
				cmd = pc_notif_commands["notify"].format(
					notif_id=notif_id,
					src=src,
					title=title,
					body=body
				)
				app.threadW.waspconn_ready_event.wait()
				app.threadW.run_command(cmd)
				del self.notifs[reply_serial]
		else:
			notif_id = args[0]
			cmd = pc_notif_commands["unnotify"].format(notif_id=notif_id)
			app.threadW.waspconn_ready_event.wait()
			app.threadW.run_command(cmd)
