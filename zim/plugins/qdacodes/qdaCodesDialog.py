# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>
# Licence : GPL or same as Zim

from __future__ import with_statement

import gtk

from zim.gui.widgets import ui_environment, Dialog, InputEntry, ScrolledWindow, HPaned, Button  
from zim.signals import DelayedCallback


from qdaCodesTreeView import QdaCodesTreeView
from qdaTagListTreeView import TagListTreeView



class QdaCodesDialog(Dialog):

    def __init__(self, plugin):
        if ui_environment['platform'] == 'maemo':
            defaultsize = (800, 480)
        else:
            defaultsize = (900, 500)

        Dialog.__init__(self, plugin.ui, _('Qda Codes'),  # T: dialog title
            buttons=gtk.BUTTONS_CLOSE, help=':Plugins:Qda Codes',
            defaultwindowsize=defaultsize)

        self.plugin = plugin
        if ui_environment['platform'] == 'maemo':
            self.resize(800, 480)
            # Force maximum dialog size under maemo, otherwise
            # we'll end with a too small dialog and no way to resize it
            
        hbox = gtk.HBox(spacing=5)
        self.vbox.pack_start(hbox, False)
        self.hpane = HPaned()
        self.uistate.setdefault('hpane_pos', 75)
        self.hpane.set_position(self.uistate['hpane_pos'])
        self.vbox.add(self.hpane)

        # Code list
        self.qda_codes = QdaCodesTreeView(self.ui, plugin)
        self.qda_codes.set_headers_visible(True)  # Fix for maemo
        self.hpane.add2(ScrolledWindow(self.qda_codes))

        # Tag list
        self.tag_list = TagListTreeView(self.qda_codes)
        self.hpane.add1(ScrolledWindow(self.tag_list))

        # Filter input
        hbox.pack_start(gtk.Label(_('Filter') + ': '), False)  # T: Input label
        filter_entry = InputEntry()
        filter_entry.set_icon_to_clear()
        hbox.pack_start(filter_entry, False)
        filter_cb = DelayedCallback(500, lambda o: self.qda_codes.set_filter(filter_entry.get_text()))
        filter_entry.connect('changed', filter_cb)

        # Statistics label
        # self.statistics_label = gtk.Label()
        # hbox.pack_end(self.statistics_label, False)

        export_button = gtk.Button(_('_Export') )
        export_button.connect_object('clicked', self.qda_codes.get_data_as_page, self.qda_codes )
        hbox.pack_end(export_button, False )


        def on_qdacodes_changed(o):
            self.qda_codes.refresh()
            self.tag_list.refresh(self.qda_codes)
            # set_statistics()

        callback = DelayedCallback(10, on_qdacodes_changed)
            # Don't really care about the delay, but want to
            # make it less blocking - should be async preferably
            # now it is at least on idle

        self.connectto(plugin, 'qdacodes-changed', callback)

        # Async solution fall because sqlite not multi-threading
        # (see also todo item for async in DelayedSignal class)

        # ~ def async_call(o):
            # ~ from zim.async import AsyncOperation
            # ~ op = AsyncOperation(on_qdacodes_changed, args=(o,))
            # ~ op.start()
        # ~ self.connectto(plugin, 'qdacodes-changed', async_call)

    def do_response(self, response):
        self.uistate['hpane_pos'] = self.hpane.get_position()
        # self.uistate['only_show_act'] = self.act_toggle.get_active()
        Dialog.do_response(self, response)

