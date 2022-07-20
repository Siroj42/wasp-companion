import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

import threading

session_bus_address = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION)

pc_notif_commands = {
	"notify": 'GB({{"t":"notify","id":"{notif_id}","src":"{src}","title":"{title}","body":"{body}"}})',
	"unnotify": 'GB({{"t":"notify-","id":"{notif_id}"}})'
}

class MainThread(threading.Thread):
	def __init__(self, app_object):
		super().__init__()
		self.app = app_object
		self.notifs = {}

	def run(self):
		conn = Gio.DBusConnection.new_for_address_sync(
			session_bus_address,
			Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
		)

		conn.call_sync(
			"org.freedesktop.DBus",
			"/org/freedesktop/DBus",
			"org.freedesktop.DBus.Monitoring",
			"BecomeMonitor",
			GLib.Variant(
				"(asu)",
				[
					[
						"type='method_return'",
						"type='method_call', interface='org.freedesktop.Notifications', member='Notify'",
						"type='method_call', interface='org.gtk.Notifications', member='AddNotification'",
						"type='signal', interface='org.freedesktop.Notifications', member='NotificationClosed'"
					],
					0
				]
			),
			None,
			Gio.DBusCallFlags.NONE,
			-1,
			None
		)
		conn.add_filter(self.msg_filter)

		self.loop = GLib.MainLoop()
		self.loop.run()

	def quit(self):
		self.loop.quit()

	def msg_filter(self, conn, message, incoming):
		msg_type = message.get_message_type()
		msg_body = message.get_body()

		if msg_type == Gio.DBusMessageType.METHOD_CALL:
			if message.get_path() == "/org/freedesktop/Notifications":
				src = msg_body[0]
				title = msg_body[3]
				body = msg_body[4]
				for n in self.notifs:
					if self.notifs[n] == {"src": src, "title": title, "body": body}:
						return
				self.notifs[str(message.get_serial())] = {"src": src, "title": title, "body": body}
			else:
				print("Got a GTK Notification")
				print(msg_body)
				src = msg_body[0]
				notif_id = msg_body[1]
				title = msg_body[2]["title"]
				body = msg_body[2]["body"]
				cmd = pc_notif_commands["notify"].format(
					notif_id=notif_id,
					src=src,
					title=title,
					body=body
				)
				self.app.threadW.waspconn_ready_event.wait()
				self.app.threadW.run_command(cmd)
		elif msg_type == Gio.DBusMessageType.METHOD_RETURN:
			reply_serial = str(message.get_reply_serial())
			if reply_serial in self.notifs:
				notif_id = msg_body[0]
				src = self.notifs[reply_serial]["src"]
				title = self.notifs[reply_serial]["title"]
				body = self.notifs[reply_serial]["body"]
				cmd = pc_notif_commands["notify"].format(
					notif_id=notif_id,
					src=src,
					title=title,
					body=body
				)
				self.app.threadW.waspconn_ready_event.wait()
				self.app.threadW.run_command(cmd)
				del self.notifs[reply_serial]
		elif msg_type == Gio.DBusMessageType.SIGNAL:
			notif_id = msg_body[0]
			cmd = pc_notif_commands["unnotify"].format(notif_id=notif_id)
			self.app.threadW.waspconn_ready_event.wait()
			self.app.threadW.run_command(cmd)
