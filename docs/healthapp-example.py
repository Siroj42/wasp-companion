from dasbus.loop import EventLoop
from dasbus.connection import SessionMessageBus

import threading
import time
import datetime

class HealthApp1():
	with open("../src/dbus/HealthApp1.xml") as file:
		__dbus_xml__ = file.read()

		def __init__(self):
			self.available_apps = {}

		def Announce(self, bus_name, app_name):
			if not bus_name in self.available_apps:
				self.available_apps[bus_name] = app_name

		def UnAnnounce(self, bus_name):
			if bus_name in self.available_apps:
				del self.available_apps[bus_name]

if __name__ == "__main__":
	bus = SessionMessageBus()
	health_app1 = HealthApp1()
	bus.publish_object("/io/github/siroj42/HealthApp1", health_app1)
	bus.register_service("io.github.siroj42.HealthApp")

	loop = EventLoop()
	loop_thread = threading.Thread(target=loop.run)
	loop_thread.start()

	selected_app = None
	try:
		while not selected_app:
			print("Available apps: ")
			for bus_name in health_app1.available_apps:
				name = health_app1.available_apps[bus_name]
				print("{} (bus name: {})".format(name, bus_name))
			inp = input("App interface to register ('r' to refresh_list): ")
			if inp != "r" and inp in health_app1.available_apps:
				selected_app = inp
	except KeyboardInterrupt:
		loop.quit()
		exit()

	companion_app = bus.get_proxy(
		selected_app,					# bus name
		"/io/github/siroj42/Health1",	# path
		"io.github.siroj42.Health1"		# interface
	)
	# Get all activities from the last hour
	activities = companion_app.GetActivities(datetime.datetime.fromtimestamp(int(time.time()-3600)).astimezone().isoformat())

	for activity in activities:
		print("{} : {} for {} minutes".format(
			activity[1],
			activity[0],
			activity[2] / 60
		))
	loop.quit()
