import threading
import gi
import time

gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

pc_music_commands = {
	"play": 'GB({"t":"musicstate","state":"play"})',
	"pause": 'GB({"t":"musicstate","state":"pause"})',
	"info": 'GB({{"t":"musicinfo","artist":"{artist}","track":"{track}"}})'
}

class MainThread(threading.Thread):
	def __init__(self, app_object):
		global app
		global thread
		thread = self
		threading.Thread.__init__(self)
		app = app_object

	def run(self):
		self.manager = Playerctl.PlayerManager()
		self.manager.connect('name-appeared', on_player_appeared)
		self.manager.connect('player-vanished', on_player_vanished)
		for name in self.manager.props.player_names:
			on_player_appeared(self.manager, name)

		self.main = GLib.MainLoop()
		self.main.run()

	def process_watchcmd(self, n):
		if n == "pause":
			self.current_player.pause()
		elif n == "play":
			self.current_player.play()
		elif n == "next":
			self.current_player.next()
		elif n == "previous":
			self.current_player.previous()

	def quit(self):
		self.main.quit()

def on_player_appeared(manager, name):
	thread.current_player = Playerctl.Player.new_from_name(name)
	thread.current_player.connect('playback-status::playing', on_play, thread.manager)
	thread.current_player.connect('playback-status::paused', on_pause, thread.manager)
	thread.current_player.connect('metadata', on_metadata_change, thread.manager)

	on_metadata_change(None, None, None)
	if thread.current_player.get_property("playback-status") == Playerctl.PlaybackStatus(0):
		on_play(None, None, None)
	else:
		on_pause(None, None, None)

	thread.manager.manage_player(thread.current_player)

def on_player_vanished(manager, player):
	return

def on_play(player, status, manager):
	app.threadW.waspconn_ready_event.wait()
	app.threadW.run_command(pc_music_commands["play"])

def on_pause(player, status, manager):
	app.threadW.waspconn_ready_event.wait()
	app.threadW.run_command(pc_music_commands["pause"])

def on_metadata_change(player, metadata, manager):
	artist = thread.current_player.get_artist()
	track = thread.current_player.get_title()
	app.threadW.waspconn_ready_event.wait()
	if artist and track:
		app.threadW.run_command(pc_music_commands["info"].format(artist=artist.replace('"','\\"'), track=track.replace('"','\\"')))
	else:
		app.threadW.run_command(pc_music_commands["info"].format(artist="", track=""))
