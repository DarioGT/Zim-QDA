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


    def do_exportQdaCodes(self):

        if self.qda.plugin.preferences['export_tags'] :
            self.do_exportQdaTags()

        if self.qda.plugin.preferences['export_tocs'] :
            self.do_table_of_contents()
            
        if self.qda.plugin.preferences['export_maps'] :
            self.do_exportQdaMaps()


        
    def do_exportQdaTags(self):

        zPages = {}
        myTag = ''
        myCode = ''

        # Borra el Namespace de exportacion
        masterPath = self.qda.plugin.preferences['namespace_qda']
        self.qda.plugin.ui.delete_page(Path(masterPath)) 


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
                zPages[ myTag ] += '__{0}__  {1}\n'.format(source, nroCita)
                zPages[ myTag ] += '{}\n\n'.format(row['citation'].decode('utf-8'))
            except: 
                pass 


        masterPageIx = '====== Summary ======\nCreated: {}\n\n'.format(datetime.now().isoformat())

        masterPath = self.qda.plugin.preferences['namespace_qda']
        for tag in zPages:
            zPage = zPages[ tag ]
            newpage = self.qda.plugin.ui.new_page_from_text(zPage,'{0}:CODE-{1}'.format(masterPath, tag), open_page=False)
            pagename = newpage.name
            
            # Se asegura q sea absoluto ( issue  Win - Linux ) 
            if pagename[0] != ':' : pagename = ':' + pagename 
            masterPageIx += '__{}__\n'.format(pagename)

        masterPageIx += '\n'

        self.qda.plugin.ui.append_text_to_page(masterPath , masterPageIx)

        # Open de index page ( QDA Namespace root )
        # newpage = Path(masterPath)
        # self.qda.ui.open_page(newpage)

    def do_table_of_contents(self):

        masterPath = self.qda.plugin.preferences['namespace_qda']
        sWhere = 'tag = \'{}\''.format(NOTE_AUTOTITLE)
        sOrder = 'source, citnumber'
        mySource = ''

        masterPageIx = '\n====== Tables of contents ======\n'

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


    def do_exportQdaMaps(self):

        # Viene formateado absoluto :xxx:xxx  
        masterPath = self.qda.plugin.preferences['namespace_map']
        sWhere = 'codetype != \'S\''

        # Crea las paginas de base 
        self.addDummyPage('{0}'.format(masterPath) ) 
        self.addDummyPage('{0}:codes'.format(masterPath) ) 
        self.addDummyPage('{0}:tags'.format(masterPath) )

        for row in self.qda.plugin.list_mapcodes( whereStmt=sWhere ):

            # Format description
            code = row['code'].decode('utf-8')
            codetype = row['codetype'].decode('utf-8')

            # Codes : qdaMapas:codes:a:abcd 
            if codetype == 'C':   
                # Pagina de separacion alfabetica 
                pagename = '{0}:codes:{1}'.format(masterPath, code[0] )
                self.addDummyPage( pagename )

                pagetext = '&{0}'.format( code )
                pagename = '{0}:codes:{1}:{2}'.format(masterPath, code[0], code  )

            # Tags : qdaMapas:tags:xxxx 
            else : 
                pagetext = '&{0}'.format( code )
                pagename = '{0}:tags:{1}'.format(masterPath,  code  )

            self.addDummyPage( pagename, pagetext )
            
    def addDummyPage( self, pagename, pagetext = 'qdaAuto'): 
        """Crea la pagina en la estructura, si existe, no la toca 
        """

        newpage = self.qda.plugin.ui.notebook.get_page( Path( pagename ))
        if newpage.hascontent: return 

        self.qda.plugin.ui.append_text_to_page( pagename, pagetext )

        # newpage = self.qda.plugin.ui.new_page_from_text( pagetext , pagename, open_page=False)
        # pagename = newpage.name
        # self.qda.plugin.ui.append_text_to_page( pagename, pagetext )