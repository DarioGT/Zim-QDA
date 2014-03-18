# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>
# Licence : GPL or same as Zim

import gobject
import logging
import re

# from zim.notebook import Path
from zim.config import check_class_allow_empty


logger = logging.getLogger('zim.plugins.qdacodes')


ui_actions = (
    # name, stock id, label, accelerator, tooltip, read only
    # T: menu item
    ('show_qda_codes', 'zim-qda-codes', _('Qda Codes'), '', _('Qda Codes'), True),
)


ui_xml = '''
<ui>
    <menubar name='menubar'>
        <menu action='view_menu'>
            <placeholder name="plugin_items">
                <menuitem action="show_qda_codes" />
            </placeholder>
        </menu>
    </menubar>
    <toolbar name='toolbar'>
        <placeholder name='tools'>
            <toolitem action='show_qda_codes'/>
        </placeholder>
    </toolbar>
</ui>
'''

_tag_re = re.compile(r'(?<!\S)@(\w+)\b', re.U)


_NO_TAGS = '__no_tags__'  # Constant that serves as the "no tags" tag - _must_ be lower case

#     ----------------------------------------------------------------------
#      ----------     Db


SQL_FORMAT_VERSION = (0, 6)
SQL_CREATE_TABLES = '''
create table if not exists qdacodes (
    id INTEGER PRIMARY KEY,
    source INTEGER,
    parent INTEGER,
    haschildren BOOLEAN,
    open BOOLEAN,
    prio INTEGER,
    citation TEXT,
    tags TEXT,
    description TEXT
);
'''
#===============================================================================
# QdaCodesPlugin
#===============================================================================

# define signals we want to use - (closure type, return type and arg types)

__gsignals__ = {
    'qdacodes-changed': (gobject.SIGNAL_RUN_LAST, None, ()),
}

plugin_info = {
    'name': _('Qda Codes'),  # T: plugin name
    'description': _('''\
This plugin adds a dialog showing all open QDA codes in
this notebook. Open codes can be  items marked with tags like "QDA" or "CODE".

'''),  # T: plugin description
    'author': 'Dario Gomez',
    'help': 'Plugins:Qda Codes'
}

plugin_preferences = (

    # # key, type, label, default, validation

    # T: label for plugin preferences dialog
    ('tag_by_page', 'bool', _('Turn page name into tags for code items'), True),

    # T: label for plugin preferences dialog - labels are e.g. "CODE1", "CODE2",  ...
    ('labels', 'string', _('Labels marking codes'), 'NQ, NE', check_class_allow_empty),

    # T: subtree to search for codes - default is the whole tree (empty string means everything)
    ('included_subtrees', 'string', _('Subtree(s) to index'), '', check_class_allow_empty),

    # T: subtrees of the included subtrees to *not* search for codes - default is none
    ('excluded_subtrees', 'string', _('Subtree(s) to ignore'), '', check_class_allow_empty),
)

# Rebuild database table if any of these preferences changed.
# Rebuild always??
_rebuild_on_preferences = [
    'labels',
    'included_subtrees',
    'excluded_subtrees'
    ]

