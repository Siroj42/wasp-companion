from dasbus.server.interface import accepts_additional_arguments
from dasbus.loop import EventLoop
from dasbus.connection import SessionMessageBus

import threading
import time

class HealthAPI1():
	with open("/app/share/dbus/HealthAPI1.xml") as file:
		__dbus_xml__ = file.read()

	def __init__(self, app_object):
	    self.app = app_object

	@accepts_additional_arguments
	def GetActivities(self, since, call_info):
		day_since_values = [since]
		while day_since_values[len(day_since_values)-1]+24*60*60 <= time.time():
			day_since_values.append(day_since_values[len(day_since_values)-1] + 24*60*60)

		data = []
		for s in day_since_values:
			offset = time.localtime(s).tm_gmtoff
			wasp_day = s + offset - 946684800
			day = self.app.threadW.run_command("for x, d in enumerate(wasp.system.steps.data({})): print(x, d)\r".format(wasp_day), expect_return=True)[3:]
			for i in range(len(day)):
				day[i] = int(day[i].split(" ")[1])
			data.append(day)

		activities = []
		for i in range(len(day_since_values)):
			day_start_local = time.localtime(day_since_values[i])
			day_start = day_since_values[i] - day_start_local.tm_hour * 3600 + day_start_local.tm_min * 60 + day_start_local.tm_sec
			day = data[i]
			activity_steps = 0
			activity_length = 0
			activity_timestamp = 0
			for i in range(len(day)):
				timestamp = day_start + 360*i
				if timestamp < since:
					continue
				if day[i] == 0 and activity_steps > 0:
					activity = ("walking", -1, activity_timestamp, -1, -1, -1, -1, 360*activity_length, activity_steps)
					activities.append(activity)
					activity_steps, activity_length, activity_timestamp = 0, 0, 0
				elif day[i] > 0:
					activity_steps += day[i]
					activity_length += 1
					if activity_timestamp == 0:
						activity_timestamp = timestamp
			if activity_steps > 0:
				activity = ("walking", -1, activity_timestamp, -1, -1, -1, -1, 360*activity_length, activity_steps)
				activities.append(activity)

		return activities

class MainThread(threading.Thread):
	def __init__(self, app_object):
		super().__init__()
		self.app = app_object
		self.proxy_v1 = None

	def run(self):
		self.bus = SessionMessageBus()
		health_api1 = HealthAPI1(self.app)
		self.bus.publish_object("/io/github/siroj42/HealthAPI1", health_api1)

		dbus_proxy = self.bus.get_proxy(
			"org.freedesktop.DBus",
			"/org/freedesktop/DBus"
		)
		dbus_proxy.NameOwnerChanged.connect(self.on_name_owner_changed)

		self.loop = EventLoop()
		self.loop.run()

	def on_name_owner_changed(self, name, old_owner, new_owner):
		if name == "io.github.siroj42.HealthApp":
			self.proxy_v1 = self.bus.get_proxy(
				"io.github.siroj42.HealthApp",
				"/io/github/siroj42/HealthApp1",
				"io.github.siroj42.HealthApp1"
			)
			try:
				self.proxy_v1.Announce(
					"io.github.siroj42.WaspCompanion",
					"Wasp Companion"
				)
			except:
				del self.proxy_v1


	def quit(self):
		if self.proxy_v1:
			self.proxy_v1.UnAnnounce("io.github.siroj42.WaspCompanion")
		self.loop.quit()
