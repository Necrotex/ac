#!/usr/bin/env python


# XXX: fix login (track it)
# XXX: comment and make code readable
# XXX: write played file <-> database match module and integrate in the GUI


							  ## Import section ##

from os import path

import os, sys, Queue, pickle, webbrowser, \
		pygtk, gtk, gtk.glade, gobject, time

from twisted.internet import gtk2reactor
gtk2reactor.install()

from twisted.internet import reactor
from twisted.web import client

import modules.myanimelist
from modules.players import get_playing

from config import ac_config
from data import *

from callbacks import \
		cb_hide_about, \
		cb_hide_login, \
		cb_hide_prefs, \
		cb_init, \
		cb_mal_login, \
		cb_mal_logout, \
		cb_refresh, \
		cb_show_about, \
		cb_show_prefs, \
		cb_webopen, \
		cb_quit


							   ### Constants ###

startup_ctls = ['list', 'edit']
tree_stati = ["current", "completed", "onHold", "planToWatch", "dropped"]


							### Initialize data ###

config = ac_config()
ui_data = gtk.glade.XML('main.glade')
mal_socket = modules.myanimelist.data_source()
context = ui_data.get_widget("statusbar").get_context_id("animecollector")
cb_init(ui_data, mal_socket, config, context)

# Load data file
pkl_data_path = path.join(path.expanduser("~"), ".animecollector.pkl")
pkl_data = dict()
if os.path.isfile(pkl_data_path) and os.path.getsize(pkl_data_path) > 0:
	f = open(pkl_data_path)
	pkl_data = pickle.load(f)
else:
	open(pkl_data_path, 'w')
	pkl_data = {}


								### Methods ###

def toggle_ctlgrp(widget, event=None):
	""" Toggle a group of controls.

	This function toggles the state of connected control groups.
	It switches connected options in the menubar and on the buttonbar,
	and shows/hides their planes.
	"""

	for ctl in startup_ctls:
		button = ui_data.get_widget('togglebutton_' + ctl)
		menuitem = ui_data.get_widget('menuitem_bars_' + ctl)
		ctl = ui_data.get_widget(ctl + 'Bar')
		
		if (widget is button) or (widget is menuitem):
			if widget.get_active():
				ctl.show()
				menuitem.set_active(True)
				button.set_active(True)
			else:
				ctl.hide()
				menuitem.set_active(False)
				button.set_active(False)


def toggle_main_win(widget, event=None):
	""" Toggles main window visibility. """

	window = ui_data.get_widget("window_main")
	if window.flags() & gtk.VISIBLE:
		window.hide()
	else:
		window.show()
	return True

def populate_tree_view(tree):
	"""
	Populatates the entries of the tree views with the animes and their stati.
	The tree parameter determines which tree is being populated.
	"""

	# XXX: still needs cleenup

	adj = {}
	columns = []

	for column in tree.get_columns():
		tree.remove_column(column)

	columns.append((gtk.TreeViewColumn('Title'), "text"))
	columns.append((gtk.TreeViewColumn('Status'), "text"))
	columns.append((gtk.TreeViewColumn('Type'), "text"))
	columns.append((gtk.TreeViewColumn('Score'), "text"))
	columns.append((gtk.TreeViewColumn('Episodes'), "text"))
	columns.append((gtk.TreeViewColumn('Progress'), "progress"))

	slist = gtk.ListStore(int, str, str, str, str, str, float)
	slist.clear()

	colcnt = 1
	for (column, ctype) in columns:
		if ctype is "text":
			cell = gtk.CellRendererText()
			column.pack_start(cell, True)
			column.add_attribute(cell, "text", colcnt)
		elif ctype is "progress":
			cell = gtk.CellRendererProgress()
			column.pack_start(cell, True)
			column.add_attribute(cell, 'value', colcnt)
		elif ctype is "pixbuf":
			cell = gtk.CellRendererPixbuf()
			column.pack_start(cell, True)
			column.add_attribute(cell, "pixbuf", colcnt)
		tree.append_column(column)
		colcnt += 1

	if tree is ui_data.get_widget("treeview_current"):
		status = 1
	if tree is ui_data.get_widget("treeview_completed"):
		status = 2
	if tree is ui_data.get_widget("treeview_onHold"):
		status = 3
	if tree is ui_data.get_widget("treeview_dropped"):
		status = 5
	if tree is ui_data.get_widget("treeview_planToWatch"):
		status = 6

	for (ident, anime) in pkl_data.iteritems():
		if anime["my_status"] is status:
			if anime["series_episodes"]:
				percentage_watched = (float(anime["my_watched_episodes"]) /
						float(anime["series_episodes"])) * 100
				watched = str(anime["my_watched_episodes"]) + "/" + \
						str(anime["series_episodes"])
			else:
				percentage_watched = 0
				watched = anime["my_watched_episodes"]

			slist.append([int(anime["series_animedb_id"]), 
					anime["series_title"],
					SERIES_STATUS[anime["series_status"]],
					SERIES_TYPE[anime["series_type"]], anime["my_score"],
					anime["my_watched_episodes"],
					percentage_watched])

	tree.set_model(slist)


							 ### Initialize GUI ###

# Initialize control groups
for ctl in startup_ctls:
	ui_data.get_widget('togglebutton_' + ctl).show()
	ui_data.get_widget('togglebutton_' + ctl).connect('toggled', toggle_ctlgrp)
	ui_data.get_widget('menuitem_bars_' + ctl).show()
	ui_data.get_widget('menuitem_bars_' + ctl).connect('toggled', toggle_ctlgrp)

ui_data.get_widget("togglebutton_list").set_active(True)

# Set up tray icon
trayicon = gtk.StatusIcon()
trayicon.set_from_file("ac.ico")
trayicon.connect("activate", toggle_main_win)
trayicon.set_visible(True)


# Connect widgecs to callbacks
ui_data.signal_autoconnect({
		"on_menuitem_file_quit_activate": cb_quit,
		"on_menuitem_edit_preferences_activate": cb_show_prefs,
		"on_button_preferences_clicked": cb_show_prefs,
		"on_button_prefs_cancel_clicked": cb_hide_prefs,
		"on_button_mal_refresh_clicked": cb_refresh,
		"on_button_mal_login_clicked": cb_mal_login,
		"on_button_mal_logout_clicked": cb_mal_logout,
		"on_button_login_cancel_clicked": cb_hide_login,
		"on_button_login_ok_clicked": cb_mal_login,
		"on_menuitem_help_about_activate": cb_show_about,
		"on_aboutdialog_response": cb_hide_about,
		"on_button_mal_clicked": cb_webopen,
		"on_button_ac_clicked": cb_webopen })


# Set up widget according to configuration
if config.mal['autologin']:
	self.mal_login()

if config.ui['tray_onstartup']:
	ui_data.get_widget("window_main").hide()

if config.ui['tray_onclose']:
	ui_data.get_widget("window_main").connect("delete-event", toggle_main_win)
else:
	ui_data.get_widget("window_main").connect("delete-event", quit)

# Load anime list tree views
for tree in tree_stati:
	populate_tree_view(ui_data.get_widget("treeview_" + tree))

# Eat the cake
reactor.run()


						   ### Class declarations ###

# class leeroyjenkins(object):
# 
# 
# 	def mal_updated(self, success):
# 		if success:
# 			self.pkl_data.update(mal_socket.return_as_dic())
# 			mal_list_pickle = file('mal.pkl', 'w')
# 			pickle.dump(self.pkl_data, mal_list_pickle)
# 			self.statusMessage("List retrieved.")
# 		else:
# 			self.statusMessage("Failed to retrive list.")
# 		self.working("malUpdate", REMOVE)
# 		for tree in tree_stati:
# 			populate_tree_view(ui_data.get_widget("treeview_" + tree))
# 
# 
# 	def sanDate(self, thedate):
# 
# 
# 		if type(thedate) is date:
# 			if thedate:
# 				return thedate
# 			else:
# 				return None
# 		if type(thedate) is str:
# 			if not thedate == "0000-00-00":
# 				year = thedate.split("-")[0]
# 				month = thedate.split("-")[1]
# 				day = thedate.split("-")[2]
# 				if not year == "0000":
# 					if not month == "00":
# 						if not day == "00":
# 							return date.fromtimestamp(time.mktime(time.strptime(thedate,
# 																	"%Y-%m-%d")))
# 						else:
# 							return None
# 					else:
# 						return None
# 				else:
# 					return None
# 			else:
# 				return None
# 
# 	def sanUnicode(self, thestring):
# 		if thestring:
# 			return unicode(thestring)
# 		else:
# 			return None
# 
# 	def getValue(self, tree, node):
# 		endnode = tree.getElementsByTagName(node)
# 		if endnode:
# 			if endnode[0]:
# 				if endnode[0].firstChild:
# 					if endnode[0].firstChild.nodeValue:
# 						return endnode[0].firstChild.nodeValue
# 					else:
# 						return None
# 				else:
# 					return None
# 			else:
# 				return None
# 		else:
# 			return None
# 
# 
# 
# 	def statusMessage(self, message):
# 		ui_data.get_widget("statusbar").push(self.context, message)
# 
# 
# 	def getWidget(self, widgetname):
# 		return ui_data.get_widget(widgetname)
# 
# 	def getCurrentTreeview(self, deathnote):
# 		widget = deathnote.get_tab_label(deathnote.get_nth_page(deathnote.get_current_page()))
# 		if widget == ui_data.get_widget("label_current"):
# 			return ui_data.get_widget("treeview_current")
# 		elif widget == ui_data.get_widget("label_completed"):
# 			return ui_data.get_widget("treeview_completed")
# 		elif widget == ui_data.get_widget("label_onHold"):
# 			return ui_data.get_widget("treeview_onHold")
# 		elif widget == ui_data.get_widget("label_planToWatch"):
# 			return ui_data.get_widget("treeview_planToWatch")
# 
# 	def callMAL(self, uri, method="POST", postdata=None, headers=None):
# 		return client.getPage(uri, method=method, cookies=self.cookiesMAL,
# 							  postdata=postdata, agent="animecollector",
# 							  headers=headers)
# 
# 	def working(self, ident, add):
# 		if add:
# 			self.worklist.append(ident)
# 		else:
# 			self.worklist.remove(ident)
# 
# 
# 	def switchBar(self, widget, event=None):
# 		for bar in startup_ctls:
# 			button = ui_data.get_widget("togglebutton_" + bar)
# 			menuitem = ui_data.get_widget("menuitem_bars_" + bar)
# 			bar = ui_data.get_widget(bar + "Bar")
# 			if widget == button or widget == menuitem:
# 				if widget.get_active():
# 					bar.show()
# 					menuitem.set_active(True)
# 					button.set_active(True)
# 				else:
# 					bar.hide()
# 					menuitem.set_active(False)
# 					button.set_active(False)
# 
# letsdothis = leeroyjenkins()
