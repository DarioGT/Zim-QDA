'''
Created on Mar 13, 2015

@author: dario
'''

from zim.notebook import Path
from qdaSettings import sluglify
from qdaSettings import NOTE_MARK, NOTE_AUTOTITLE

from qdaExportTools import doCodeRelations, getTag 

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
        self.zPage = {  
            'name' : pageName, 
            'pageid': self.pageid, 
            'sources' : [ pageName ], 
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

                doCodeRelations( self.zPage, linkA, tag2, myTag )


        #  Agrega las relaciones del archivo con los tags 
        for myTag in self.zPage['tags']:
            myLink = '{0} -> {1}'.format( pageName, myTag)
            self.zPage.get('links').append( myLink )


        return self.zPage 



    def do_ShowMap(self, page):
        """ Exporta el mapa del documento  ( ver wiki )
        """
        self.page = page   


        # La idea es q sea por fuente en la idenxacion del documento                  
        self.pageName = sluglify( self.page.name.split(':')[-1] ) 
        self.zPage = {  
            'name' : self.pageName, 
            'pageid': 0, 
            'links'   : [], 
            'sources' : [], 
            'tags'    : [], 
            'codes'   : [],
            }


        sWhere = 'code = \'{0}\''.format( self.pageName )
        for row in self.plugin.list_mapcodes( whereStmt=sWhere ):

            # Format description
            code = row['code'].decode('utf-8')
            ctype = row['codetype'].decode('utf-8')

            # Inserta el codigo central del mapa 
            self.addMapRelCode( code, ctype  )

            # Recorre hacia adelante u atraz
            self.getLinks( code, True  )
            self.getLinks( code, False  )

        return self.zPage 


    def getLinks(self, code, goFF ):
        # recorre recursivamente el arbol en una unica direccion 
        if goFF: 
            sWhere = 'code1 = \'{0}\''.format( code )
        else: sWhere = 'code2 = \'{0}\''.format( code )

        for row in self.plugin.list_maprels( whereStmt=sWhere ):

            # recupera los codigos y los tipos 
            code1 = row['code1'].decode('utf-8')
            ctype1 = row['ctype1'].decode('utf-8')

            #  Los autores siempre son code1, no se dib
            if ctype1 == 'S' and code1 != self.pageName :  continue 

            code2 = row['code2'].decode('utf-8')
            ctype2 = row['ctype2'].decode('utf-8')

            # Inserta la relacion y verifica si el nodo ya existe para no caer en un loop infinito 
            if not self.addMapRel( goFF, code1, code2, ctype1, ctype2 ): 
                continue 

            # Continua navegando en la misma direccion, ff ahora mi nodo2 es mi base 
            if goFF: 
                code = code2
            else: code = code1
            self.getLinks( code, goFF )


    def addMapRel( self, goFF, code1, code2, ctype1, ctype2  ):
        # Inserta los vinculos para el mapa generico 

        myLink = '{0} -> {1}'.format( code1, code2 )
        if myLink not in self.zPage.get( 'links' ): 
            self.zPage.get('links').append( myLink )

        if goFF: 
            # Si voy FF solo tengo q insertar y verificar el segundo codigo ( si existe para )
            code = code2
            ctype = ctype2
        else:
            # Si voy back solo tengo q verificar el primero codigo 
            code = code1
            ctype = ctype1

        return self.addMapRelCode( code,  ctype  )


    def addMapRelCode( self, code, ctype  ):
        # Inserta los codigos para el mapa generico 

        if ctype == 'T': subCol = 'tags'
        elif ctype == 'S': subCol = 'sources'
        elif ctype == 'C': subCol = 'codes'

        if code not in self.zPage[ subCol ]: 
            self.zPage[subCol].append( code )
            return True 

        return False 



