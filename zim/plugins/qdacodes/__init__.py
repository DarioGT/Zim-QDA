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

from qdaExport import doQdaExport  

from qdaExportMapDoc import doQdaExportMapDoc
from qdaExportTools import doCodeRelations, doDotFile, doViewDotFile, getTag

from qdaSettings import logger, ui_actions, ui_xml, _tag_re, _NO_TAGS, SQL_FORMAT_VERSION, SQL_CREATE_TABLES
from qdaSettings import NOTE_MARK, NOTE_AUTOTITLE

TAG_MARK = ""

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
        self.allow_map = False

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

        # Si el indexamiento es en batch, no permite indexamiento automatico
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

        excluded.append(self.preferences['namespace_qda'])
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

                self.index.db.execute('DROP TABLE "qdamapcodes"')
                self.index.db.execute('DROP TABLE "qdamaprels"')
                self.index.db.execute('DROP TABLE "qdamapsource"')
            except:
                logger.exception('Could not drop table:')
            else:
                self.db_initialized = False
        else:
            try:
                self.index.db.execute('DROP TABLE "qdacodes"')

                self.index.db.execute('DROP TABLE "qdamapcodes"')
                self.index.db.execute('DROP TABLE "qdamaprels"')
                self.index.db.execute('DROP TABLE "qdamapsource"')
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
                self._insertTag(path, 0, codes)

            # qdaMap 
            if self.allow_map : 
                qdaExp = doQdaExportMapDoc( self   )
                zPage = qdaExp.do_MapDocCodes( page )
                with self.index.db_commit:
                    self._insertMap( zPage)

        if codes or qCodesfound:
            self.emit('qdacodes-changed')


    def _insertTag(self, path, parentid, children):
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
                    (path.id, parentid, cNumber) + tuple(qCode)
                )
            except: 
                pass 


    def _insertMap(self, zPage):
        # Helper function to insert codes in table
        c = self.index.db.cursor()

        # Crea la coleccion de codigos 

        pageid = zPage['pageid']
        qdamapcodes  = [tuple([ zPage['name'] ,'S'])]

        for myTag in zPage['tags']:
            qdamapcodes.append( tuple([myTag ,'T']))

        for myTag in zPage['codes']:
            qdamapcodes.append( tuple([myTag ,'C']))

        # Inserta los codigos y sus dependencias a la pagina 
        for myTag in qdamapcodes:
            try: 
                c.execute(
                    'insert into qdamapcodes( code, codetype )'
                    'values (?, ?)', tuple(myTag)
                )
            except:  pass 

            try: 
                c.execute(
                    'insert into qdamapsource( code, source )'
                    'values (?, ?)', tuple( [myTag[0], pageid ] )
                )
            except:  pass 

        # Inserta las relaciones entre codigos 
        for myTag in zPage['links']:
            try: 
                c.execute(
                    'insert into qdamaprels( code1, code2 )'
                    'values (?, ?)', tuple( myTag.split(' -> '))
                )
            except:  pass 
            
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
                tag = getTag(item)
                if len (tag) > 0:
                    codes += self._addNewCode( unicode( item ) , index , tag)

#         print codes
#         print '----------------'

        return codes



    def _addNewCode(self, items, index , tag0):
        """
        Una misma linea de codigo puede contener mas de un codigo separado por ;
        La citacion es la misma,
        En caso de ser un titulo, no hay citacion solo el tag
        """

        codes = []
        citation = None

        # DGT: Asume que vienen diferentes codigos de la linea (;) y los separa
        # 1503 Se dejan tal cual, el manejo del mapa se ocupa 
        # for item in items.split(';'): item = item.strip();

        # Tomas los valores antes de los dos puntos 
        item = items # .split(':')[0]
        tag = getTag(items)

        if ( not tag ) or ( len(tag) == 0):
#             continue 
            return codes 
            
        # Aisgna el tag por defecto en caso de ser una continuacion de lineas
        if tag[0] not in ( NOTE_MARK, TAG_MARK ):
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

#           Dgt 1503 La busqueda de las citaciones es lenta y realmente no me esta siriviendo de mucho 
#           citation = citation or self._getCitation(index + 1)
            citation= ""

            codes.append((item, citation , tag[1:]))


        return codes


    def _getCitation(self, index):
        # Obtiene el texto de la citacion
        citation = ''

        for item in self.lines[index: ]:
            if type(item) is tuple:
                citation += item[0] + '\n'

            # Al encontrar una marca retorna
            elif item[0] in ( NOTE_MARK, TAG_MARK ) :
                return citation

        # Elimina el ultimo \n
        return citation[0:-2]


    def _flatten_para(self, nodeAux):
        # Returns a list which is a mix of normal lines of text and
        # tuples for checkbox items. Checkbox item tuples consist of
        # the checkbox type, the indenting level and the text.
        items = []

        if nodeAux.tag in ('p', 'div' ):
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

            for subNode in nodeAux.getchildren():
                # QDA Tag                  
                if subNode.tag in ('tag' ):
                    sNode = subNode.text
                    sAux = subNode.tail.split()

                    # Si Es una lista de tags solo toma el primero  
                    if len( sAux ) > 0: 
                        sAux = sAux[0]
                        # no toma comas 
                        if sAux[0] in ( ',',';','.'): 
                            sAux = ""
                    else: sAux = ""

                    lnAux = '{0} {1}'.format (sNode, sAux )
                    items.append( lnAux )

                else: 
                    # items += self._flatten_para(childList)
                    subText = self._flatten_para(subNode)
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

        with index.db_commit:
            # Borra las relaciones con la fuente 
            cursor.execute('delete from qdamapsource where source=?', (path.id,))

            # Borra los codigos sin relaciones en las fuentes 
            cursor.execute('delete from qdamapcodes where code not in (Select code from qdamapsource)')

            # Borra los codigos sin relaciones en las fuentes 
            cursor.execute('delete from qdamaprels where code1 not in (Select code from qdamapsource)')
            cursor.execute('delete from qdamaprels where code2 not in (Select code from qdamapsource)')

        if qCodesfound and _emit:
            self.emit('qdacodes-changed')

        return qCodesfound



    def list_codes(self, parent=None, orderBy='source, citnumber', whereStmt='1=1'):
        '''List codes
        @param parent: the parent qCode (as returned by this method) or C{None} to list all top level codes
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


    def list_mapcodes(self, whereStmt='1=2'):
        '''List mapcodes 
        @returns: a list of map codes at this level as sqlite Row objects
        '''
        if self.db_initialized:
            cursor = self.index.db.cursor()
            sqlStmt = 'select * from qdamapcodes where {0} order by codetype'.format(whereStmt)
            cursor.execute(sqlStmt)
            for row in cursor:
                yield row

    def list_maprels(self, whereStmt='1=2', orderBy='code1'):
        '''List mapcodes 
        @returns: a list of map codes at this level as sqlite Row objects
        '''
        if self.db_initialized:
            cursor = self.index.db.cursor()


            sqlStmt = "select code1, code2, c1.codetype as ctype1 , c2.codetype as ctype2"
            sqlStmt += " from qdamaprels as r, qdamapcodes as c1, qdamapcodes as c2"
            sqlStmt += " where r.code1 = c1.code"
            sqlStmt += " and r.code2 = c2.code"
            sqlStmt += " and {0} order by {1}".format(whereStmt, orderBy)
            cursor.execute(sqlStmt)
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
        self.allow_map = True

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
        self.allow_map = False 

        # Flush + Reload will also initialize qda codes
        if not finished:
            self.db_initialized = False
            return

    def qda_codes_show(self):

        if not self.db_initialized:
            self.qda_index_all()

        dialog = QdaCodesDialog.unique(self, plugin=self)
        dialog.present()


    def qda_index_page(self):

        if not self.db_initialized:
            self.qda_index_all()
            return
        
        # Controla el indexamiento por paginas 
        self.allow_index = True
        self.allow_map = False
        self.ui.save_page()

        # Retoma el valor de la conf 
        self.allow_index = not self.preferences['batch_clasification']

        # Genera el mapa  doQdaExportMapDoc  
        qdaExp =  doQdaExportMapDoc( self  )

        zPage = qdaExp.do_MapDocCodes( self.ui.page )
        with self.index.db_commit:
            self._insertMap(zPage)

        dotFile = doDotFile( zPage )
        doViewDotFile( self.ui.page.name, self.ui.page.folder, dotFile  )


    def qda_show_map(self):

        # Genera el mapa  doQdaExportMapDoc  
        qdaExp =  doQdaExportMapDoc( self  )
        
        zPage = qdaExp.do_ShowMap( self.ui.page )
        dotFile = doDotFile( zPage )
        doViewDotFile( self.ui.page.name, self.ui.page.folder, dotFile  )

# Need to register classes defining gobject signals
gobject.type_register(QdaCodesPlugin)  # @UndefinedVariable



