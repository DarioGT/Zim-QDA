# -*- coding: utf-8 -*-

# Copyright 2011 NorfCran <norfcran@gmail.com>

from zim.notebook import Path
from zim.plugins import PluginClass


class BookmarksPlugin(PluginClass):

    _ui_merge_ids = ()

    plugin_info = {
        'name': _('Bookmarks'),  # T: plugin name
        'description': _('Allows definition of 10 Bookmarks accessed through Alt+(0-9) and from a menubar (Go).\nBookmark number => Page'),  # T: plugin description
        'author': 'NorfCran\nmodify by Dario Gomez',
        'help': 'Plugins:Bookmarks',
    }

    plugin_preferences = (
               ('bookmark_0', 'string', 'Bookmark 0', ':Home'),
               ('bookmark_1', 'string', 'Bookmark 1', ':Home'),
               ('bookmark_2', 'string', 'Bookmark 2', ':Home'),
               ('bookmark_3', 'string', 'Bookmark 3', ':Home'),
               ('bookmark_4', 'string', 'Bookmark 4', ':Home'),
               ('bookmark_5', 'string', 'Bookmark 5', ':Home'),
               ('bookmark_6', 'string', 'Bookmark 6', ':Home'),
               ('bookmark_7', 'string', 'Bookmark 7', ':Home'),
               ('bookmark_8', 'string', 'Bookmark 8', ':Home'),
               ('bookmark_9', 'string', 'Bookmark 9', ':Home'),
    )

    def __init__(self, ui):
        PluginClass.__init__(self, ui)

    def generate_ui_xml(self):
        ui_xml_template = '''
        <menubar name='menubar'>
                <menu action='go_menu'>
                        <placeholder name='plugin_items'>
                                <menuitem action='bookmark_%i'/>
                        </placeholder>
                </menu>
        </menubar>
'''
        ui_xml = ""
        for i in range(10):
            ui_xml += ui_xml_template % i
        ui_xml = "<ui>\n" + ui_xml + "\n</ui>"
        return ui_xml

    def generate_ui_actions(self):
        # in oder to provide dynamic key binding assignment the initiation is made in the plugin class --> DONE
        ui_actions = ()
        for i in range(10):
            label = self.preferences['bookmark_%i' % i]
            ui_actions += ('bookmark_%i' % i, None, _('%s' % label), '<Alt>%i' % i, '', False),
        return ui_actions

    def initialize_ui(self, ui):
        if ui.ui_type == 'gtk':
            ui_actions = self.generate_ui_actions()
            ui.add_actions(ui_actions, self)
            ui_xml = self.generate_ui_xml()
            ui.add_ui(ui_xml, self)

    def do_preferences_changed(self):
        ui = self.ui 
        
        if ui.ui_type == 'gtk':
            self.remove_ui()

            ui_actions = self.generate_ui_actions()
            ui.add_actions(ui_actions, self)

            ui_xml = self.generate_ui_xml()
            ui.add_ui(ui_xml, self)

    def remove_ui(self):
        try:
            self.ui.remove_ui(self)
            self.ui.remove_actiongroup(self)
        except:
#           logger.exception('Exception while updating preferences %s', self)
            pass

    def bookmark_0(self):
        self.go_to_bookmark(self.preferences['bookmark_0'])

    def bookmark_1(self):
        self.go_to_bookmark(self.preferences['bookmark_1'])

    def bookmark_2(self):
        self.go_to_bookmark(self.preferences['bookmark_2'])

    def bookmark_3(self):
        self.go_to_bookmark(self.preferences['bookmark_3'])

    def bookmark_4(self):
        self.go_to_bookmark(self.preferences['bookmark_4'])

    def bookmark_5(self):
        self.go_to_bookmark(self.preferences['bookmark_5'])

    def bookmark_6(self):
        self.go_to_bookmark(self.preferences['bookmark_6'])

    def bookmark_7(self):
        self.go_to_bookmark(self.preferences['bookmark_7'])

    def bookmark_8(self):
        self.go_to_bookmark(self.preferences['bookmark_8'])

    def bookmark_9(self):
        self.go_to_bookmark(self.preferences['bookmark_9'])

    def go_to_bookmark(self, page):
        self.ui.open_page(Path(page))
