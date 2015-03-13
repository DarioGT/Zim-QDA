'''
Created on Mar 13, 2015

@author: dario
'''

from zim.notebook import Path
from qdaSettings import NOTE_AUTOTITLE, sluglify
import zim.datetimetz as datetime


class doQdaExport(object):
    '''
    classdocs
    '''

    def __init__(self, qda ):
        '''
        Constructor
        '''

        self.qda = qda 


    def do_delete_QDA(self):
        """ Borra el Namespace de exportacion
        """
        if not self.qda.plugin.preferences['add_on_export']: 
            masterPath = self.qda.plugin.preferences['namespace']
            self.qda.plugin.ui.delete_page(Path(masterPath)) 

        
    def do_export(self):

        zPages = {}
        myTag = ''
        myCode = ''


        self.do_delete_QDA()

        sWhere = self.qda._getWStmt(self.qda.plugin.preferences['qda_labels'])
        sOrder = 'tag, description, source, citnumber'

        for row in self.qda.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):

            path = self.qda.plugin.get_path(row)
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
            try:
                if code != myCode:
                    myCode = code
                    zPages[ myTag ] += '===== {} =====\n\n'.format(code)
            except: 
                pass 


            # Break by Page
            try: 
                zPages[ myTag ] += '[[{0}]]  **{1}**\n'.format(source, nroCita)
                zPages[ myTag ] += '{}\n\n'.format(row['citation'].decode('utf-8'))
            except: 
                pass 


        masterPageIx = '====== Summary ======\nCreated: {}\n\n'.format(datetime.now().isoformat())

        masterPath = self.qda.plugin.preferences['namespace']
        for tag in zPages:
            zPage = zPages[ tag ]
            newpage = self.qda.plugin.ui.new_page_from_text(zPage , ':{0}:CODE-{1}'.format(masterPath, tag)  , open_page=False)
            pageName = newpage.name
            
            # Se asegura q sea absoluto ( issue  Win - Linux ) 
            if pageName[0] != ':' : pageName = ':' + pageName 
            masterPageIx += '[[{}]]\n'.format(pageName)

        masterPageIx += '\n'

        self.qda.plugin.ui.append_text_to_page(masterPath , masterPageIx)

        # TOC
        if self.qda.plugin.preferences['table_of_contents'] :
            self.do_table_of_contents()
            
        if self.qda.plugin.preferences['map_codes'] :
            self.do_map_detail(True)

        if self.qda.plugin.preferences['map_pages'] :
            self.do_map_detail(False)

        # Open de index page ( QDA Namespace root )
        newpage = Path(masterPath)
        # self.qda.ui.open_page(newpage)

    def do_table_of_contents(self):

        masterPath = self.qda.plugin.preferences['namespace']
        sWhere = 'tag = \'{}\''.format(NOTE_AUTOTITLE)
        sOrder = 'source, citnumber'
        mySource = ''

        masterPageIx = '\n====== Table of contents ======\n'

        for row in self.qda.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):

            path = self.qda.plugin.get_path(row)
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

        self.qda.plugin.ui.append_text_to_page(masterPath , masterPageIx + '\n')




    def do_map_detail(self, byTag):
        """
        Por cada codigo genera las fuentes con formato record y label
        Genera una lista de codigos con su label
        genera la conexion de cada autor con los codigos
        si existen jerarquias ( listas separadas por , ) las presenta encadendas
        cuando hay conceptos jerarquizados no deberia vincularlos a la fuente
        """

        masterPath = self.qda.plugin.preferences['namespace']

        sWhere = self.qda._getWStmt(self.qda.plugin.preferences['qda_labels'])

        if byTag: 
            sOrder = 'tag, source, description'
        else :
            sOrder = 'source, tag, description'


        myTag = ''
        mySource = ''
        myCode = ''
        zPages = {}

        for row in self.qda.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):
            path = self.qda.plugin.get_path(row)
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
            try: 
                if source != mySource:
                    mySource = source
                    zPages[ myTag ][ 'sources'].append(mySource)
            except: 
                pass 

            # Break by Code ( links [[]]
            try: 
                if code != myCode:
                    myCode = code
                    myLink = [ sluglify(i.strip())  for i in code.split(',') ]
                    zPages[ myTag ][ 'links'].append([ mySource ] + myLink)
                    zPages[ myTag ][ 'codes'].extend(myLink)
            except: 
                pass 


        if byTag: 
#             masterPageIx = '\n====== Codification detail ======\n'
            prefixPage = 'MAP-CODES'

        else : 
#             masterPageIx = '\n====== Source detail ======\n'
            prefixPage = 'MAP-PAGES'


        pageName = ':{0}:{1}'.format(masterPath, prefixPage) 
        self.qda.plugin.ui.append_text_to_page( pageName , '======== {0} =========\n\n'.format( prefixPage  ) )


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
            self.qda.plugin.ui.append_text_to_page( pageName , masterPageIx + '\n')

            # Add index 
            masterPageIx = '[[{}]]\n'.format(pageName)
            pageName = ':{0}:{1}'.format(masterPath, prefixPage) 
            self.qda.plugin.ui.append_text_to_page( pageName , masterPageIx )

            # =================  Agrega el contenido despues del mapa     
        
