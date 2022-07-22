from dasbus.loop import EventLoop
from dasbus.connection import SessionMessageBus

import threading

proxy_v1 = None

class Health1():
	with open("../src/dbus/Health1.xml") as file:
		__dbus_xml__ = file.read()

	def GetActivities(self, since):
		activities = [
			('walking', -1, 1658476650, -1, -1, -1, -1, 360, 16),
			('walking', -1, 1658478090, -1, -1, -1, -1, 360, 36),
			('walking', -1, 1658480250, -1, -1, -1, -1, 1080, 98),
			('walking', -1, 1658481690, -1, -1, -1, -1, 360, 14)
		]
		return activities

def on_name_owner_changed(name, old_owner, new_owner):
	global proxy_v1

	if name == "io.github.siroj42.HealthApp":
		proxy_v1 = bus.get_proxy(
				"io.github.siroj42.HealthApp",
				"/io/github/siroj42/HealthApp1",
				"io.github.siroj42.HealthApp1"
		)
		try:
			proxy_v1.Announce(
				"org.example.CompanionApp",
				"Example Companion App"
			)
		except:
			proxy_v1 = None

if __name__ == "__main__":
	bus = SessionMessageBus()
	health_api1 = Health1()
	bus.publish_object("/io/github/siroj42/Health1", health_api1)
	bus.register_service("org.example.CompanionApp")

	dbus_proxy = bus.get_proxy(
		"org.freedesktop.DBus",
		"/org/freedesktop/DBus"
	)
	dbus_proxy.NameOwnerChanged.connect(on_name_owner_changed)

	loop = EventLoop()
	print("Entering eventloop...")
	try:
		loop.run()
	except:
		if proxy_v1:
			proxy_v1.UnAnnounce("org.example.CompanionApp")
