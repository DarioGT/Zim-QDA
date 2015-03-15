# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>
# Licence : GPL or same as Zim

import gobject
import logging
import re

# from zim.notebook import Path
from zim.config import check_class_allow_empty


logger = logging.getLogger('zim.plugins.qdacodes')

#DGT: Marca de titulos para obtener las tablas de materias 
NOTE_AUTOTITLE = 'QDATITLE'
NOTE_MARK = '%'


ui_actions = (
    # name, stock id, label, accelerator, tooltip, read only
    ('qda_codes_show', 'zim-qda', _('Qda Show'), '<shift><alt>Q', _('Qda Show'), True),
    ('qda_index_all', 'zim-qda-ix', _('Qda IndexAll'), '', _('Qda IndexAll'), True),
    ('qda_index_page', 'zim-qda-ip', _('Qda IndexPage'), '<shift><ctrl>Q', _('Qda IndexPage'), True),

    ('qda_show_map', 'zim-show-map', _('Qda ShowMap'), '<shift><ctrl>M', _('Qda ShowMap'), True),
)


ui_xml = '''
<ui>
    <menubar name='menubar'>
        <menu action='view_menu'>
            <placeholder name="plugin_items">
                <menuitem action="qda_codes_show" />
            </placeholder>
        </menu>
        <menu action='tools_menu'>
            <placeholder name='plugin_items'>
                <menuitem action='qda_index_page'/>
            </placeholder>
            <placeholder name='plugin_items'>
                <menuitem action='qda_index_all'/>
            </placeholder>

            <placeholder name='plugin_items'>
                <menuitem action='qda_show_map'/>
            </placeholder>

        </menu>
    </menubar>
    <toolbar name='toolbar'>
        <placeholder name='tools'>
            <toolitem action='qda_codes_show'/>
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
    citnumber INTEGER,
    citation TEXT,
    tag TEXT,
    description TEXT
);

create table if not exists qdamapcodes (
    id INTEGER PRIMARY KEY,
    code TEXT,
    codetype TEXT,
    unique ( code )
);

create table if not exists qdamaprels (
    id INTEGER PRIMARY KEY,
    code1 TEXT,
    code2 TEXT, 
    unique ( code1, code2 )
);

create table if not exists qdamapsource (
    id INTEGER PRIMARY KEY,
    code TEXT,
    source INTEGER
);

'''
#===============================================================================
# QdaCodesPlugin
#===============================================================================

# define signals we want to use - (closure type, return type and arg types)

__gsignals__ = {
    'qdacodes-changed': (gobject.SIGNAL_RUN_LAST, None, ()),  # @UndefinedVariable
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

    # key, type, label, default, validation
    ('all_qda', 'bool', _('Consider all tags as qdacodes'), True),

    # T: label for plugin preferences dialog - labels are e.g. "CODE1", "CODE2",  ...
    ('qda_labels', 'string', _('Labels marking codes'), 'QDA, PROTO, OL', check_class_allow_empty),

    # T: subtree to search for codes - default is the whole tree (empty string means everything)
    ('included_subtrees', 'string', _('Subtree(s) to index'), '', check_class_allow_empty),

    # T: subtrees of the included subtrees to *not* search for codes - default is none
    ('excluded_subtrees', 'string', _('Subtree(s) to ignore'), '', check_class_allow_empty),

    # T: namespace for summary 
    ('namespace_qda', 'string', _('Qda Namespace'), ':QdaCodes'),
    ('namespace_map', 'string', _('Maps Namespace'), ':QdaIndex'),

    # T: Batch code clasification 
    ('batch_clasification', 'bool', _('Batch code clasification'), True),

    ('export_tags', 'bool', _('Export summary'), False ),
    ('export_maps', 'bool', _('Export maps'), True ),
    ('export_tocs', 'bool', _('Export table of contents'), False ),
)

# Rebuild database table if any of these preferences changed.
# Rebuild always??
_rebuild_on_preferences = [
    'included_subtrees',
    'excluded_subtrees' 
    ]


def sluglify( code  ): 

    import unicodedata

    slug  = unicode( code  )
    slug = unicodedata.normalize('NFKD', slug )
    slug = slug.encode('ascii', 'ignore').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')

    return  re.sub(r'[-]+', '_', slug)    


