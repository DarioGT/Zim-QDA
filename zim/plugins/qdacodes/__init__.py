# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>
# Licence : GPL or same as Zim

from __future__ import with_statement

import gobject
import logging
import re

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


from qdaCodesDialog import QdaCodesDialog
from qdaCodesTreeView import QdaCodesTreeView
from qdaTagListTreeView import TagListTreeView

from qdaSettings import logger, ui_actions, ui_xml, _tag_re, _NO_TAGS, SQL_FORMAT_VERSION, SQL_CREATE_TABLES
from qdaSettings import NOTE_MARK, NOTE_AUTOTITLE


class QdaCodesPlugin(PluginClass):

    from qdaSettings import __gsignals__, plugin_info, plugin_preferences, _rebuild_on_preferences

    def __init__(self, ui):
        PluginClass.__init__(self, ui)
        self.codes_labels = None
        self.all_qda = True 


        self.included_re = None
        self.excluded_re = None
        self.db_initialized = False
        self._current_preferences = None

        # Permite el indexamiento de la db en batch
        self.allow_index = False

        # No se usa, se maneja todo con SQL o IN 
        # self.codes_label_re = None


    def initialize_ui(self, ui):
        if ui.ui_type == 'gtk':
            ui.add_actions(ui_actions, self)
            ui.add_ui(ui_xml, self)

    def finalize_notebook(self, notebook):
        # This is done regardsless of the ui type of the application
        self.index = notebook.index
        self.connectto_all(self.index, (
            ('initialize-db', self.initialize_db, None, SIGNAL_AFTER),
            ('page-indexed', self.index_page),
            ('page-deleted', self.remove_page),
        ))
        # We don't care about pages that are moved

        db_version = self.index.properties['plugin_qdacodes_format']
        if db_version == '%i.%i' % SQL_FORMAT_VERSION:
            self.db_initialized = True

        self._set_preferences()


    def initialize_db(self, index):

        with index.db_commit:
            index.db.executescript(SQL_CREATE_TABLES)
        self.index.properties['plugin_qdacodes_format'] = '%i.%i' % SQL_FORMAT_VERSION
        self.db_initialized = True


    def do_preferences_changed(self):
        if self._current_preferences is None or not self.db_initialized:
            return

        new_preferences = self._serialize_rebuild_on_preferences()

        # Asegura borrar la db
        if new_preferences != self._current_preferences or self.preferences['batch_clasification'] :
            self._drop_table()
        self._set_preferences()

    def _set_preferences(self):
        self._current_preferences = self._serialize_rebuild_on_preferences()

        sLabels = self.preferences['qda_labels'].split(',')
        if sLabels  :
            self.codes_labels = [ (NOTE_MARK + '{}').format(s.strip().upper()) for s in sLabels ]
        else:
            self.codes_labels = []

        self.all_qda = self.preferences['all_qda']

        # NO SE USA, se maneja todo con IN  DGT 1404
        # regex = r'^(' + '|'.join(map(re.escape, self.codes_labels)) + r')(?!\w)'
        # self.codes_label_re = re.compile(regex)

        # Si el indexamiento es en batch, no permite indexamiento onlin
        self.allow_index = not self.preferences['batch_clasification']

        # Parametros de exclusion e inclusion
        if self.preferences['included_subtrees']:
            included = [i.strip().strip(':') for i in self.preferences['included_subtrees'].split(',')]
            included.sort(key=lambda s: len(s), reverse=True)  # longest first
            included_re = '^(' + '|'.join(map(re.escape, included)) + ')(:.+)?$'
            # ~ print '>>>>>', "included_re", repr(included_re)
            self.included_re = re.compile(included_re)
        else:
            self.included_re = None

        if self.preferences['excluded_subtrees']:
            excluded = [i.strip().strip(':') for i in self.preferences['excluded_subtrees'].split(',')]
        else :
            excluded = []

        excluded.append(self.preferences['namespace'])
        excluded.sort(key=lambda s: len(s), reverse=True)  # longest first
        excluded_re = '^(' + '|'.join(map(re.escape, excluded)) + ')(:.+)?$'

        # ~ print '>>>>>', "excluded_re", repr(excluded_re)
        self.excluded_re = re.compile(excluded_re)



    def _serialize_rebuild_on_preferences(self):
        # string mapping settings that influence building the table
        string = ''
        for pref in self._rebuild_on_preferences:
            string += str(self.preferences[pref])
        return string

    def destroy(self):
        self._drop_table()
        PluginClass.destroy(self)


    def _drop_table(self):
        self.index.properties['plugin_qdacodes_format'] = 0
        if self.db_initialized:
            try:
                self.index.db.execute('DROP TABLE "qdacodes"')
            except:
                logger.exception('Could not drop table:')
            else:
                self.db_initialized = False
        else:
            try:
                self.index.db.execute('DROP TABLE "qdacodes"')
            except:
                pass


    def _excluded(self, path):
        if self.included_re and self.excluded_re:
            # judge which match is more specific
            # this allows including subnamespace of excluded namespace
            # and vice versa
            inc_match = self.included_re.match(path.name)
            exc_match = self.excluded_re.match(path.name)
            if not exc_match:
                return not bool(inc_match)
            elif not inc_match:
                return bool(exc_match)
            else:
                return len(inc_match.group(1)) < len(exc_match.group(1))
        elif self.included_re:
            return not bool(self.included_re.match(path.name))
        elif self.excluded_re:
            return bool(self.excluded_re.match(path.name))
        else:
            return False


    def index_page(self, index, path, page):

        # DGT Aqui comienza
        if not self.db_initialized: return
        if not self.allow_index: return

        if self._excluded(path): return

        # ~ print '>>>>>', path, page, page.hascontent

        qCodesfound = self.remove_page(index, path, _emit=False)
        if self._excluded(path):
            if qCodesfound:
                self.emit('qdacodes-changed')
            return

        parsetree = page.get_parsetree()
        if not parsetree:
            return

        if page._ui_object:
            dumper = get_format('wiki').Dumper()
            text = ''.join(dumper.dump(parsetree)).encode('utf-8')
            parser = get_format('wiki').Parser()
            parsetree = parser.parse(text)

        # ~ print '!! Checking for codes in', path
        codes = self._extract_codes(parsetree)
        # ~ print 'qCodeS', codes

        if codes:
            # Do insert with a single commit
            with self.index.db_commit:
                self._insert(path, 0, codes)

        if codes or qCodesfound:
            self.emit('qdacodes-changed')


    def _insert(self, page, parentid, children):
        # Helper function to insert codes in table
        c = self.index.db.cursor()
        cNumber = 0
        for qCode  in children:
            if qCode[2] != NOTE_AUTOTITLE:
                cNumber += 1
                
            try: 
                c.execute(
                    'insert into qdacodes(source, parent, citnumber, description, citation, tag)'
                    'values (?, ?, ?, ?, ?, ?)',
                    (page.id, parentid, cNumber) + tuple(qCode)
                )
            except: 
                pass 
            
    def _extract_codes(self, parsetree):
        '''Extract all codes from a parsetree.
        '''

        # DGT
        # Stack tuple indexes
        codes = []
        if not ( self.all_qda or self.codes_labels):
            return codes

        # print parsetree.tostring()
        # print '----------------'

        lines = []
        for node in parsetree.findall('*'):
            # Lines paragraph
            lines.extend(self._flatten_para(node))


        # Las genera a nivel de clase
        self.lines = lines

        # Check line by line only text lines ( tuples = citations )
        for index, item in enumerate(self.lines):
            if not type(item) is tuple:
                tag = self._getTag(item)
                if tag[0] == NOTE_MARK:
                    codes += self._addNewCode( unicode( item ) , index , tag)

#         print codes
#         print '----------------'

        return codes

    def _getTag(self, item):
        """
        El tag es el primer elemento de la linea ( separado por un espacio )
        se comparara siempre en mayusculas
        """

        return (item.split() or [''])[0].strip().upper()


    def _addNewCode(self, items, index , tag0):
        """
        Una misma linea de codigo puede contener mas de un codigo separado por ;
        La citacion es la misma,
        En caso de ser un titulo, no hay citacion solo el tag
        """

        codes = []
        citation = None

        # DGT: Asume que vienen diferentes codigos de la linea (;) y los separa
        for item in items.split(';'):
            item = item.strip();
            tag = self._getTag(item)

            if ( not tag ) or ( len(tag) == 0):
                continue 
                
            # Aisgna el tag por defecto en caso de ser una continuacion de lineas
            if tag[0] != NOTE_MARK:
                tag = tag0
                item = '{0} {1}'.format(tag, item.strip())

            # El autotitulo no tiene citation
            if tag[1:] == NOTE_AUTOTITLE :
                item = item[ len(tag) + 1: ].strip()
                codes.append((item, '' , tag[1:]))

            # Verifica q sea un tag a reportar
            elif ( self.all_qda or tag in self.codes_labels):
                # Asigna la citacion la primera vez q encuentre un codigo valido
                item = item[ len(tag) + 1: ].strip()
                citation = citation or self._getCitation(index + 1)
                codes.append((item, citation , tag[1:]))


        return codes


    def _getCitation(self, index):
        # Obtiene el texto de la citacion
        citation = ''

        for item in self.lines[index: ]:
            if type(item) is tuple:
                citation += item[0] + '\n'

            # Al encontrar una marca retorna
            elif item[0] == NOTE_MARK:
                return citation

        # Elimina el ultimo \n
        return citation[0:-2]


    def _flatten_para(self, nodeAux):
        # Returns a list which is a mix of normal lines of text and
        # tuples for checkbox items. Checkbox item tuples consist of
        # the checkbox type, the indenting level and the text.
        items = []

        if nodeAux.tag in ('p', 'div'):
            # Agrega el texto y verifica los hijos, si no hay nada viene vacio
            itAux = []
            for lnAux in (nodeAux.text or '').splitlines():
                if lnAux and lnAux[0] == NOTE_MARK:
                    itAux.append(lnAux)
            items += itAux

        elif nodeAux.tag == 'h':
            # Permite marcarlos como titulo 5
            level = nodeAux.get('level')
            if str(level) == '5':
                items += self._flatten(nodeAux).splitlines()

            else:
                # Add a AutoTitle Mark
                items.append('{0}{1} {2}{3}'.format (NOTE_MARK, NOTE_AUTOTITLE, level, self._flatten(nodeAux)))

        elif nodeAux.tag in ('mark', 'strong', 'emphasis'):
            # Add a tuple with item tag
            items.append((self._flatten(nodeAux), nodeAux.tag))

        # REcursivo segun el tipo de tag
        if nodeAux.tag in ('ul', 'ol', 'li', 'p', 'div'):
            prefix = ''
            if nodeAux.tag in ('div',):
                prefix = '\t'
            elif nodeAux.tag in ('ol', 'li'):
                prefix = '* '

            for childList in nodeAux.getchildren():
                # items += self._flatten_para(childList)
                subText = self._flatten_para(childList)
                for subLine in subText:
                    items.append((prefix + subLine[0], subLine[1]))

        return items


    def _flatten(self, node):
        # Just flatten everything to text - but ignore strike out
        text = node.text or ''
        for child in node.getchildren():
            if child.tag == 'strike':
                text += child.tail or ''
            else:
                text += self._flatten(child)  # recurs
                text += child.tail or ''
        return text.strip()



    def remove_page(self, index, path, _emit=True):
        if not self.db_initialized: return

        qCodesfound = False
        with index.db_commit:
            cursor = index.db.cursor()
            cursor.execute('delete from qdacodes where source=?', (path.id,))
            qCodesfound = cursor.rowcount > 0

        if qCodesfound and _emit:
            self.emit('qdacodes-changed')

        return qCodesfound

    def list_codes(self, parent=None, orderBy='source, citnumber', whereStmt='1=1'):
        '''List codes
        @param parent: the parent qCode (as returned by this method) or C{None} to list
        all top level codes
        @returns: a list of codes at this level as sqlite Row objects
        '''
        if parent: parentid = parent['id']
        else: parentid = 0

        if self.db_initialized:
            cursor = self.index.db.cursor()
            sqlStmt = 'select * from qdacodes where parent=? and {1} order by {0}'.format(orderBy, whereStmt)
            cursor.execute(sqlStmt , (parentid,))
            for row in cursor:
                yield row


    def get_code(self, qCodeid):
        cursor = self.index.db.cursor()
        cursor.execute('select * from qdacodes where id=?', (qCodeid,))
        return cursor.fetchone()

    def get_path(self, qCode):
        '''Get the L{Path} for the source of a qCode
        @param qCode: the qCode (as returned by L{list_codes()}
        @returns: an L{IndexPath} object
        '''
        return self.index.lookup_id(qCode['source'])

    def qda_index_all(self):

        self.db_initialized = False
        self.allow_index = True

        MessageDialog(self.ui, (
            _('Need to index the notebook'),
            # T: Short message text on first time use of qda codes plugin
            _('The index needs to be rebuild ( it may be the first time )\n'
              'Depending on the size of the notebook this can\n'
              'take up to several minutes. If you want onLine code '
              'clasification uncheck plugin paramenter //batch_clasification//.')
            # T: Long message text on first time use of qda codes plugin
        )).run()
        logger.info('qCodelist rebuild index')
        finished = self.ui.reload_index(flush=True)

        # Retoma el valor de la conf 
        self.allow_index = not self.preferences['batch_clasification']

        # Flush + Reload will also initialize qda codes
        if not finished:
            self.db_initialized = False
            return


    def qda_index_page(self):

        if not self.db_initialized:
            self.qda_index_all()
            return
        
        # Controla el indexamiento por paginas 
        self.allow_index = True
        self.ui.save_page()

        # Retoma el valor de la conf 
        self.allow_index = not self.preferences['batch_clasification']


    def qda_codes_show(self):

        if not self.db_initialized:
            self.qda_index_all()

        dialog = QdaCodesDialog.unique(self, plugin=self)
        dialog.present()


# Need to register classes defining gobject signals
gobject.type_register(QdaCodesPlugin)  # @UndefinedVariable

