# -*- coding: utf-8 -*-

# Copyright 2014 Dario Gomez  <dariogomezt at gmail dot com>
# Licence : GPL or same as Zim

from __future__ import with_statement

import gtk
import pango
import re


from zim.notebook import Path
from zim.gui.widgets import ui_environment, BrowserTreeView, encode_markup_text, decode_markup_text
from zim.gui.clipboard import Clipboard

from qdaSettings import logger, _tag_re, _NO_TAGS, NOTE_MARK, NOTE_AUTOTITLE, sluglify

import zim.datetimetz as datetime

# Borrar
_date_re = re.compile(r'\s*\[d:(.+)\]')
_NO_DATE = '9999'  # Constant for empty due date - value chosen for sorting properties


HIGH_COLOR = '#EF5151'  # red (derived from Tango style guide - #EF2929)
MEDIUM_COLOR = '#FCB956'  # orange ("idem" - #FCAF3E)
ALERT_COLOR = '#FCEB65'  # yellow ("idem" - #FCE94F)
# FIXME: should these be configurable ?


class QdaCodesTreeView(BrowserTreeView):

    MCOL_VISI = 0
    MCOL_CODE = 1
    MCOL_CITA = 2
    MCOL_PAGE = 3
    MCOL_NCIT = 4
    MCOL_RGID = 5
    MCOL_TAGS = 6

    def getColIx(self):
        self.colIx += 1
        return self.colIx - 1

    def __init__(self, ui, plugin):

        # Visible, MCOL_CODE, MCOL_CITA, MCOL_PAGE, MCOL_NCIT, MCOL_RGID, MCOL_TAGS
        self.real_model = gtk.TreeStore(bool, str, str, str, str, int, object)
        model = self.real_model.filter_new()
        model.set_visible_column(self.MCOL_VISI)
        model = gtk.TreeModelSort(model)

        BrowserTreeView.__init__(self, model)
        self.ui = ui
        self.plugin = plugin
        self.filter = None
        self.tag_filter = None
        self.label_filter = None
        self._tags = {}
        self._labels = {}


# Description column
        cell_renderer = gtk.CellRendererText()
        cell_renderer.set_property('ellipsize', pango.ELLIPSIZE_END)

        column = gtk.TreeViewColumn(_('QdaCode'), cell_renderer, markup=self.MCOL_CODE)
        column.set_resizable(True)
        column.set_sort_column_id(self.MCOL_CODE)
        column.set_expand(True)
        column.set_min_width(200)
        self.append_column(column)
        self.set_expander_column(column)

# Citation  column
        cell_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Text'), cell_renderer, text=self.MCOL_CITA)

        column.set_resizable(True)
        column.set_sort_column_id(self.MCOL_CITA)
        column.set_min_width(200)
        column.set_max_width(300)

        self.append_column(column)

# Rendering for page name column
        cell_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Page'), cell_renderer, text=self.MCOL_PAGE)
        column.set_sort_column_id(self.MCOL_PAGE)
        self.append_column(column)


# Nro Citation in the page
        cell_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_(' # '), cell_renderer, text=self.MCOL_NCIT)
        column.set_sort_column_id(self.MCOL_NCIT)
        self.append_column(column)


# Finalize
        self.refresh()

        # HACK because we can not register ourselves :S
        self.connect('row_activated', self.__class__.do_row_activated)


    def refresh(self):
        '''Refresh the model based on index data'''
        # Update data
        self._clear()
        self._append_codes(None, None, {})

        # Make tags case insensitive
        tags = sorted((t.lower(), t) for t in self._tags)
        prev = ('', '')
        for tag in tags:
            if tag[0] == prev[0]:
                self._tags[prev[1]] += self._tags[tag[1]]
                self._tags.pop(tag[1])
            prev = tag

        # Set view
        self._eval_filter()  # keep current selection
        self.expand_all()

    def _clear(self):
        self.real_model.clear()  # flush
        self._tags = {}
        self._labels = {}

    def _append_codes(self, code, iter, path_cache):
        """ Agrega los codigos en la ventana 
        """

        sWhere = self._getWStmt(self.plugin.preferences['qda_labels'])
        sOrder = 'source, citnumber'

        for row in self.plugin.list_codes(parent=code, orderBy=sOrder, whereStmt=sWhere):

            if row['source'] not in path_cache:
                path = self.plugin.get_path(row)
                if path is None:
                    continue
                else:
                    path_cache[row['source']] = path

            path = path_cache[row['source']]

            # Update labels
            label = row['tag']
            self._labels[label] = self._labels.get(label, 0) + 1

            # Update tag count
            tags = path.parts
            for tag in tags:
                self._tags[tag] = self._tags.get(tag, 0) + 1

            #  Code ( description )
            nroCita = "{0:03d}".format(row['citnumber'])
            description = self.get_code_description(row)

            # Insert all columns
            # Visible, MCOL_CODE, MCOL_CITA, MCOL_PAGE, MCOL_NCIT, MCOL_RGID, MCOL_TAGS
            modelrow = [ True, description , row['citation'].replace('\n', ';')  , path.name, nroCita, row['id'], tags ]

            modelrow[0] = self._filter_item(modelrow)
            myiter = self.real_model.append(iter, modelrow)

    def get_code_description(self, row):
        """ Linea de descripcion de codigo
        """
        return '{0}{1} {2}'.format(NOTE_MARK, row['tag'], row['description'])

    def set_filter(self, string):
        # TODO allow more complex queries here - same parse as for search
        if string:
            inverse = False
            if string.lower().startswith('not '):
                # Quick HACK to support e.g. "not @waiting"
                inverse = True
                string = string[4:]
            self.filter = (inverse, string.strip().lower())
        else:
            self.filter = None
        self._eval_filter()

    def get_labels(self):
        '''Get all labels that are in use
        @returns: a dict with labels as keys and the number of codes
        per label as value
        '''
        return self._labels

    def get_tags(self):
        '''Get all tags that are in use
        @returns: a dict with tags as keys and the number of codes
        per tag as value
        '''
        return self._tags

    def get_n_codes(self):
        '''Get the number of codes in the list
        @returns: total number
        '''
        counter = [0]
        def count(model, path, iter):
            counter[0] += 1
        self.real_model.foreach(count)
        return counter[0]


    def set_tag_filter(self, tags=None, labels=None):
        if tags:
            self.tag_filter = [tag.lower() for tag in tags]
        else:
            self.tag_filter = None

        if labels:
            self.label_filter = [label.lower() for label in labels]
        else:
            self.label_filter = None

        self._eval_filter()

    def _eval_filter(self):
        logger.debug('Filtering with labels: %s tags: %s, filter: %s', self.label_filter, self.tag_filter, self.filter)

        def filter(model, path, iter):
            visible = self._filter_item(model[iter])
            model[iter][self.MCOL_VISI] = visible
            if visible:
                parent = model.iter_parent(iter)
                while parent:
                    model[parent][self.MCOL_VISI] = visible
                    parent = model.iter_parent(parent)

        self.real_model.foreach(filter)
        self.expand_all()

    def _filter_item(self, modelrow):
        # This method filters case insensitive because both filters and
        # text are first converted to lower case text.


        description = modelrow[self.MCOL_CODE].decode('utf-8').lower()
        pagename = modelrow[self.MCOL_PAGE].decode('utf-8').lower()
        tags = [t.lower() for t in modelrow[self.MCOL_TAGS]]

        visible = True
        if self.label_filter:
            # Any labels need to be present
            for label in self.label_filter:
                if label in description:
                    break
            else:
                visible = False  # no label found

        if visible and self.tag_filter:
            # Any tag should match
            if (_NO_TAGS in self.tag_filter and not tags) \
            or any(tag in tags for tag in self.tag_filter):
                visible = True
            else:
                visible = False

        if visible and self.filter:
            # And finally the filter string should match
            # FIXME: we are matching against markup text here - may fail for some cases
            inverse, string = self.filter
            match = string in description or string in pagename
            if (not inverse and not match) or (inverse and match):
                visible = False

        return visible

    def do_row_activated(self, path, column):
        model = self.get_model()
        page = Path(model[path][self.MCOL_PAGE])
        text = self._get_raw_text(model[path])
        self.ui.open_page(page)
        self.ui.mainwindow.pageview.find(text)

    def _get_raw_text(self, code):
        id = code[self.MCOL_RGID]
        row = self.plugin.get_code(id)
        return self.get_code_description(row)

    def do_initialize_popup(self, menu):
        item = gtk.ImageMenuItem('gtk-copy')
        item.connect('activate', self.copy_to_clipboard)
        menu.append(item)
        self.populate_popup_expand_collapse(menu)

    def copy_to_clipboard(self, *a):
        '''Exports currently visible elements from the codes list'''
        logger.debug('Exporting to clipboard current view of qda codes.')
        text = self.get_visible_data_as_csv()
        Clipboard.set_text(text)
            # TODO set as object that knows how to format as text / html / ..
            # unify with export hooks

    def get_visible_data_as_csv(self):
        text = ""
#         for indent, prio, desc, date, page in self.get_visible_data():
        for indent, desc, date, page in self.get_visible_data():
            desc = decode_markup_text(desc)
            desc = '"' + desc.replace('"', '""') + '"'
#             text += ",".join((prio, desc, date, page)) + "\n"
            text += ",".join((desc, date, page)) + "\n"
        return text


    def get_visible_data(self):
        rows = []

        def collect(model, path, iter):
            indent = len(path) - 1  # path is tuple with indexes

            row = model[iter]
#             prio = row[self.MCOL_NCIT]
            code = row[self.MCOL_CODE].decode('utf-8')
            cita = row[self.MCOL_CITA].decode('utf-8').replace('\n', ';')
            page = row[self.MCOL_PAGE].decode('utf-8')

            rows.append((indent, code, cita, page))

        model = self.get_model()
        model.foreach(collect)

        return rows

    def _getWStmt(self, baseWhere):
        """ Toma los codigos definidos en la conf y los coviernte en un where, 
            en caso de q todos las marcas se tomen como codigos,  solo elimina los titulos (schema)
        """

        sWhere = 'tag != \'{}\''.format( NOTE_AUTOTITLE )
        if len( baseWhere ) > 0: 
            sWhere = ''
            for s in baseWhere.split(','):
                sWhere += '\'{}\','.format(s.strip().upper())
    
            sWhere = 'tag in ({})'.format(sWhere[:-1])

        return sWhere


    def do_delete_QDA(self):
        """ Borra el Namespace de exportacion
        """
        if not self.plugin.preferences['add_on_export']: 
            masterPath = self.plugin.preferences['namespace']
            self.plugin.ui.delete_page(Path(masterPath)) 


    def get_data_as_page(self, me):
        """ Opcion de exportacion
        """

        zPages = {}
        myTag = ''
        myCode = ''

        self.do_delete_QDA()

        sWhere = self._getWStmt(self.plugin.preferences['qda_labels'])
        sOrder = 'tag, description, source, citnumber'

        for row in self.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):

            path = self.plugin.get_path(row)
            if path is None: continue

            # Format description
            tag = row['tag'].decode('utf-8')
            code = row['description'].decode('utf-8')
            source = path.name
            nroCita = "{0:03d}".format(row['citnumber'])

            # Break by Tag
            if tag != myTag:
                myTag = tag
                zPages[ myTag ] = '====== {} ======\n'.format(tag)
                zPages[ myTag ] += 'Created {} \n\n'.format(datetime.now().isoformat())

            # Break by Code
            if code != myCode:
                myCode = code
                zPages[ myTag ] += '===== {} =====\n\n'.format(code)

            # Break by Page
            zPages[ myTag ] += '[[{0}]]  **{1}**\n'.format(source, nroCita)
            zPages[ myTag ] += '{}\n\n'.format(row['citation'].decode('utf-8'))


        masterPageIx = '====== Summary ======\nCreated: {}\n\n'.format(datetime.now().isoformat())

        masterPath = self.plugin.preferences['namespace']
        for tag in zPages:
            zPage = zPages[ tag ]
            newpage = self.plugin.ui.new_page_from_text(zPage , ':{0}:CODE-{1}'.format(masterPath, tag)  , open_page=False)
            pageName = newpage.name
            
            # Se asegura q sea absoluto ( issue  Win - Linux ) 
            if pageName[0] != ':' : pageName = ':' + pageName 
            masterPageIx += '[[{}]]\n'.format(pageName)

        masterPageIx += '\n'

        self.plugin.ui.append_text_to_page(masterPath , masterPageIx)

        # TOC
        if self.plugin.preferences['table_of_contents'] :
            self.do_table_of_contents()
            
        if self.plugin.preferences['map_codes'] :
            self.do_map_detail(True)

        if self.plugin.preferences['map_pages'] :
            self.do_map_detail(False)

        # Open de index page ( QDA Namespace root )
        newpage = Path(masterPath)
        self.ui.open_page(newpage)

    def do_table_of_contents(self):

        masterPath = self.plugin.preferences['namespace']
        sWhere = 'tag = \'{}\''.format(NOTE_AUTOTITLE)
        sOrder = 'source, citnumber'
        mySource = ''

        masterPageIx = '\n====== Table of contents ======\n'

        for row in self.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):

            path = self.plugin.get_path(row)
            if path is None: continue

            code = row['description'].decode('utf-8')

            # Break by source
            source = path.name
            if source != mySource:
                mySource = source
                masterPageIx += '\n[[:{}]]\n'.format(source)
                masterPageIx += '===== {} =====\n'.format(code[1:])

            else :
                try:
                    indent = '\t' * (int(code[0]) - 1)
                except: indent = ''
                masterPageIx += '{0}{1}\n'.format(indent, code[1:])

        self.plugin.ui.append_text_to_page(masterPath , masterPageIx + '\n')


    def do_map_detail(self, byTag):
        """
        Por cada codigo genera las fuentes con formato record y label
        Genera una lista de codigos con su label
        genera la conexion de cada autor con los codigos
        si existen jerarquias ( listas separadas por , ) las presenta encadendas
        cuando hay conceptos jerarquizados no deberia vincularlos a la fuente
        """

        masterPath = self.plugin.preferences['namespace']

        sWhere = self._getWStmt(self.plugin.preferences['qda_labels'])

        if byTag: 
            sOrder = 'tag, source, description'
        else :
            sOrder = 'source, tag, description'


        myTag = ''
        mySource = ''
        myCode = ''
        zPages = {}

        for row in self.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):
            path = self.plugin.get_path(row)
            if path is None: continue

            # Format description
            tag = row['tag'].decode('utf-8').strip()
            code = row['description'].decode('utf-8').strip()
            source = path.name 

            # Solo la marca, por ejemplo Keywords 
            if len (code) == 0: 
                continue

            if not byTag:
                # Break by Source ( Invierte las variables ) 
                sAux = source
                source = tag 
                tag = sAux 
                
            # Break by Tag
            if tag != myTag:
                myTag = tag
                mySource = ''
                myCode = ''

                zPages[ myTag ] = { 'sources' : [], 'codes' : [], 'links' : [] }

            # Break by source
            if source != mySource:
                mySource = source
                zPages[ myTag ][ 'sources'].append(mySource)


            # Break by Code ( links [[]]
            if code != myCode:
                myCode = code
                myLink = [ sluglify(i.strip())  for i in code.split(',') ]
                zPages[ myTag ][ 'links'].append([ mySource ] + myLink)
                zPages[ myTag ][ 'codes'].extend(myLink)


        if byTag: 
#             masterPageIx = '\n====== Codification detail ======\n'
            prefixPage = 'MAP-CODES'

        else : 
#             masterPageIx = '\n====== Source detail ======\n'
            prefixPage = 'MAP-PAGES'

        pageName = ':{0}:{1}'.format(masterPath, prefixPage) 
        self.plugin.ui.append_text_to_page( pageName , '======== {0} =========\n\n'.format( prefixPage  ) )


        # sort ( vector )
        zPagesSort = []          
        for tag in zPages:
            zPagesSort.append(tag)
        zPagesSort.sort()

        for tag in zPagesSort:
            zPage = zPages[ tag ]

            masterPageIx = '======= {} =======\n\n'.format(tag)
            masterPageIx += 'digraph {rankdir=LR;node [shape=register]\n\n//sources\n'

            zPage['sources'] = list(set(zPage['sources']))
            zPage['sources'].sort()
            for source in zPage['sources']:
                masterPageIx += '\t{0} \t[label="{1}"]\n'.format( sluglify(source), source )


            masterPageIx += '\n//QdaCodes\nnode [shape=oval]\n'
            zPage['codes'] = list(set(zPage['codes']))
            zPage['codes'].sort()
            for code in zPage['codes']:
                masterPageIx += '\t{0} \t[label="{1}"]\n'.format( sluglify(code), code  )


            masterPageIx += '\n//QdaLinks\n'

            # Aplana los links para no agregar codigos duplicados
            myLinks = []
            for link in zPage['links']:
                for i in range(0, len (link) - 1):
                    myLinks.append('{0} -> {1}'.format( sluglify(link[i]), sluglify(link[i + 1])))

            myLinks = list(set(myLinks))
            myLinks.sort()
            for link in myLinks:
                masterPageIx += '\t{}\n'.format(link)

            masterPageIx += '}\n'

            # Crea la pagina con el fuente del graphviz
            pageName =  ':{0}:{1}:{2}'.format(masterPath, prefixPage, tag) 
            self.plugin.ui.append_text_to_page( pageName , masterPageIx + '\n')

            # Add index 
            masterPageIx = '[[{}]]\n'.format(pageName)
            pageName = ':{0}:{1}'.format(masterPath, prefixPage) 
            self.plugin.ui.append_text_to_page( pageName , masterPageIx )

