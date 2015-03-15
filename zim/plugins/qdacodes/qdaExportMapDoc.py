'''
Created on Mar 13, 2015

@author: dario
'''

from zim.notebook import Path
from qdaSettings import sluglify
from qdaSettings import NOTE_MARK, NOTE_AUTOTITLE

from qdaExportTools import doCodeRelations

SEP__TAG = ';'


class doQdaExportMapDoc(object):
    '''
    classdocs
    '''

    def __init__(self, plugin ):
        '''
        Constructor
        '''

        self.plugin = plugin
        self.ui = plugin.ui 


    def do_MapDocCodes(self, page):
        """ Exporta el mapa del documento  ( ver wiki )
        """

        self.page = page   
        self.path = self.ui.notebook.index.lookup_path(self.page )
        self.pageid = self.path.id    

        # La idea es q sea por fuente en la idenxacion del documento                  
        sOrder = 'source, tag, description'
        sWhere = 'tag <> \'{1}\' and source = {0}'.format( self.pageid, 'QDATITLE' )

        pageName = sluglify( self.page.name.split(':')[-1] ) 
        zPage = {  
            'name' : pageName, 
            'pageid': self.pageid, 
            'sources' : [ pagename ], 
            'tags' : [], 
            'links' : [], 
            'codes' : [] 
        }

        for row in self.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):

            # Elimina los comentarios 
            myCode = row['description'].decode('utf-8').split(':')[0].strip() 
            if len (myCode) == 0: continue

            # Lo guarda de Bk pues pueden venir varios ; en la linea 
            tag0 = row['tag'].decode('utf-8').strip() 

            # Separa las relaciones directas al tag 
            myCodeA = [ j.strip() for j in myCode.split(SEP__TAG) ]
            for i  in range(0, len(myCodeA)):
                linkA = myCodeA[ i ] 

                # Si no es la primera cadena 
                if i > 0: 
                    tag2 = getTag( linkA )
                    if len( tag2 ) > 1 : 
                        linkA = linkA[len(tag2):].strip()
                        tag2 = tag2[1:].strip() 
                else: tag2 = tag0 

                if len( tag2 ) == 0 : tag2 = tag0
                myTag = sluglify(tag2)

                doCodeRelations( zPage, linkA, tag2, myTag )

        return zPage 

    def do_ShowMap(self, page):
        """ Exporta el mapa del documento  ( ver wiki )
        """
        self.page = page   

        # La idea es q sea por fuente en la idenxacion del documento                  
        pageName = sluglify( self.page.name.split(':')[-1] ) 
        zPage = {  
            'name' : pageName, 
            'pageid': 0, 
            'links'   : [], 
            'sources' : [], 
            'tags'    : [], 
            'codes'   : [],
            }


        sWhere = 'code = \'{1}\''.format( pageName )
        for row in self.qda.plugin.list_mapcodes( whereStmt=sWhere ):

            # Format description
            code = row['code'].decode('utf-8')
            ctype = row['codetype'].decode('utf-8')

            addMapRelCode( self, zPage, code, ctype  )

            # Recorre hacia adelante u atraz
            self.getLinks( zPage, code, True  )
            self.getLinks( zPage, code, False  )

        return zPage 

    def getLinks(self, zPage, code, goFF ):
        # recorre recursivamente el arbol en una unica direccion 
        if goFF: 
            sWhere = 'code1 = \'{1}\''.format( pageName )
        else: sWhere = 'code2 = \'{1}\''.format( pageName )

        for row in self.qda.plugin.list_maprels( whereStmt=sWhere ):

            # recupera los codigos y los tipos 
            code1 = row['code1'].decode('utf-8')
            code2 = row['code2'].decode('utf-8')
            ctype1 = 'C' # row['codetype1'].decode('utf-8')
            ctype2 = 'C' # row['codetype2'].decode('utf-8')

            # Inserta la relacion y verifica si el nodo ya existe para no caer en un loop infinito 
            if not self.addMapRel( zPage, goFF, code1, code2, ctype1, ctype2 ): 
                break

            if not self.getLinks(self, zPage, code, goFF ): 
                break 

        return zPage 


    def addMapRel( self, zPage, goFF, code1, code2, ctype1, ctype2  ):
        # Inserta los vinculos para el mapa generico 

        myLink = '{0} -> {1}'.format( code1, code2 )
        if myLink not in zPage.get( 'links' ): 
            zPage.get('links').append( myLink )

        if goFF: 
            # Si voy FF solo tengo q insertar y verificar el segundo codigo ( si existe para )
            code = code2
            ctype = ctype2
        else:
            # Si voy back solo tengo q verificar el primero codigo 
            code = code1
            ctype = ctype1

        return self.addMapRelCode( self, zPage, code,  ctype  )


    def addMapRelCode( self, zPage, code, ctype  ):
        # Inserta los codigos para el mapa generico 

        if ctype == 'T': subCol = 'tags'
        elif ctype == 'S': subCol = 'sources'
        elif ctype == 'C': subCol = 'codes'

        if code not in zPage[ subCol ]: 
            zPage[subCol].append( myCode )
            return true 

        return false 



