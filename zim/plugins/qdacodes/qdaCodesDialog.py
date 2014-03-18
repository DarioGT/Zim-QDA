# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>  
# Licence : GPL or same as Zim 

from __future__ import with_statement

import gobject
import gtk
import pango
import logging
import re

import zim.datetimetz as datetime
from zim.utils import natural_sorted
from zim.parsing import parse_date
from zim.plugins import PluginClass
from zim.notebook import Path
from zim.gui.widgets import ui_environment, \
    Dialog, MessageDialog, \
    InputEntry, Button, IconButton, MenuButton, \
    BrowserTreeView, SingleClickTreeView, ScrolledWindow, HPaned, \
    encode_markup_text, decode_markup_text
from zim.gui.clipboard import Clipboard
from zim.signals import DelayedCallback, SIGNAL_AFTER
from zim.formats import get_format, UNCHECKED_BOX, CHECKED_BOX, XCHECKED_BOX
from zim.config import check_class_allow_empty

from zim.plugins.calendar import daterange_from_path

from qdaCodesTreeView import QdaCodesTreeView
from qdaTagListTreeView import TagListTreeView

from qdaSettings import logger, ui_actions, ui_xml, _tag_re, _NO_TAGS, SQL_FORMAT_VERSION, SQL_CREATE_TABLES


class QdaCodesDialog(Dialog):

    def __init__(self, plugin):
        if ui_environment['platform'] == 'maemo':
            defaultsize = (800, 480)
        else:
            defaultsize = (550, 400)

        Dialog.__init__(self, plugin.ui, _('Qda Codes'), # T: dialog title
            buttons=gtk.BUTTONS_CLOSE, help=':Plugins:Qda Codes',
            defaultwindowsize=defaultsize )
        
        self.plugin = plugin
        if ui_environment['platform'] == 'maemo':
            self.resize(800,480)
            # Force maximum dialog size under maemo, otherwise
            # we'll end with a too small dialog and no way to resize it
        hbox = gtk.HBox(spacing=5)
        self.vbox.pack_start(hbox, False)
        self.hpane = HPaned()
        self.uistate.setdefault('hpane_pos', 75)
        self.hpane.set_position(self.uistate['hpane_pos'])
        self.vbox.add(self.hpane)

        # Task list
        self.qda_codes = QdaCodesTreeView(self.ui, plugin )
        self.qda_codes.set_headers_visible(True) # Fix for maemo
        self.hpane.add2(ScrolledWindow(self.qda_codes))

        # Tag list
        self.tag_list = TagListTreeView(self.qda_codes)
        self.hpane.add1(ScrolledWindow(self.tag_list))

        # Filter input
        hbox.pack_start(gtk.Label(_('Filter')+': '), False) # T: Input label
        filter_entry = InputEntry()
        filter_entry.set_icon_to_clear()
        hbox.pack_start(filter_entry, False)
        filter_cb = DelayedCallback(500,
            lambda o: self.qda_codes.set_filter(filter_entry.get_text()))
        filter_entry.connect('changed', filter_cb)

        # Dropdown with options - TODO
        #~ menu = gtk.Menu()
        #~ showtree = gtk.CheckMenuItem(_('Show _Tree')) # T: menu item in options menu
        #~ menu.append(showtree)
        #~ menu.append(gtk.SeparatorMenuItem())
        #~ showall = gtk.RadioMenuItem(None, _('Show _All Items')) # T: menu item in options menu
        #~ showopen = gtk.RadioMenuItem(showall, _('Show _Open Items')) # T: menu item in options menu
        #~ menu.append(showall)
        #~ menu.append(showopen)
        #~ menubutton = MenuButton(_('_Options'), menu) # T: Button label
        #~ hbox.pack_start(menubutton, False)


        # Statistics label
        self.statistics_label = gtk.Label()
        hbox.pack_end(self.statistics_label, False)


        def set_statistics():
            total, stats = self.qda_codes.get_statistics()
            text = ngettext('%i open item', '%i open items', total) % total  
                # T: Label for statistics in Qda Codes, %i is the number of codes
            text += ' (' + '/'.join(map(str, stats)) + ')'
            self.statistics_label.set_text(text)

        set_statistics()

        def on_qdacodes_changed(o):
            self.qda_codes.refresh()
            self.tag_list.refresh(self.qda_codes)
            set_statistics()

        callback = DelayedCallback(10, on_qdacodes_changed)
            # Don't really care about the delay, but want to
            # make it less blocking - should be async preferably
            # now it is at least on idle
        self.connectto(plugin, 'qdacodes-changed', callback)

        # Async solution fall because sqlite not multi-threading
        # (see also todo item for async in DelayedSignal class)

        #~ def async_call(o):
            #~ from zim.async import AsyncOperation
            #~ op = AsyncOperation(on_qdacodes_changed, args=(o,))
            #~ op.start()
        #~ self.connectto(plugin, 'qdacodes-changed', async_call)

    def do_response(self, response):
        self.uistate['hpane_pos'] = self.hpane.get_position()
        # self.uistate['only_show_act'] = self.act_toggle.get_active()
        Dialog.do_response(self, response)

