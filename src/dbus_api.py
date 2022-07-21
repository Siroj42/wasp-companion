from dasbus.server.interface import accepts_additional_arguments
from dasbus.loop import EventLoop
from dasbus.connection import SessionMessageBus

import threading
import time

class HealthAPI():
	__dbus_xml__ = """
		<node>
			<interface name="io.github.siroj42.WaspCompanion.HealthAPI1">
				<method name="GetActivities">
					<arg direction="in" name="since" type="u" />
					<arg direction="out" name="activity" type="a(siiiiiiii)" />
				</method>
			</interface>
		</node>
	"""

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

	def run(self):
		bus = SessionMessageBus()
		health_api = HealthAPI(self.app)
		bus.publish_object("/io/github/siroj42/WaspCompanion/HealthAPI1", health_api)

		self.loop = EventLoop()
		self.loop.run()

	def quit(self):
		self.loop.quit()
