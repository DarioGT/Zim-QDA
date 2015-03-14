'''
Created on Mar 13, 2015

@author: dario
'''

from zim.notebook import Path
from qdaSettings import sluglify
from qdaSettings import NOTE_MARK, NOTE_AUTOTITLE

TAG_MARK = ""
SEPLISTA = '-'
SEP__TAG = ';'
SEP_CODE = ','


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
            'tags' : [], 'links' : [], 'codes' : [] }

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


def doCodeRelations( zPage, linkA, tag, myTag ):

    # Separa los conceptos jerarquicos 
    linkB = [ j.strip() for j in linkA.split(SEP_CODE) ]
    for i in range(0, len(linkB)):
        code = linkB[ i ]

        # Split a primer nivel Debe tener un tag 
        if SEPLISTA in code and i == 0  : 
            myCodeB = [ j.strip() for j in code.split(SEPLISTA) ] 
            for codeB in myCodeB :
                addMapLink( myTag, codeB, zPage, True )

        # Tiene q dividir el ultimo nodo 
        elif SEPLISTA in code and i == (len (linkB) - 1)   : 
            myCodeB = [ j.strip() for j in code.split(SEPLISTA) ] 
            codeA = linkB[ i - 1 ]
            for codeB in myCodeB :
                addMapLink( codeA, codeB, zPage )

        # Primer nivel con tag 
        elif i == 0 and tag != '=': 
            addMapLink ( myTag , code, zPage, True )

        # Primer nivel sin tag, no hace nada pues se hara con base en el tag anterior 
        elif i == 0 and tag == '=': 
            continue 

        # Caso normal de un link q debe encadenarse con el nivel anterior 
        elif i > 0  : 
            codeB = linkB[ i - 1 ]
            addMapLink ( codeB , code, zPage )

def addMapLink ( myCode1, myCode2, zPage , isTag = False  ): 

    myCode1 = sluglify(myCode1)[:20]
    myCode2 = sluglify(myCode2)[:20]

    if len(myCode1)==0 or len(myCode2)==0:
        return 

    addQCode( myCode1, zPage, isTag )
    addQCode( myCode2, zPage, False  )

    myLink = '{0} -> {1}'.format( myCode1, myCode2)
    if myLink not in zPage.get( 'links' ): 
        zPage.get('links').append( myLink )

def addQCode( myCode, zPage, isTag  ):

    subCol = 'codes'
    if isTag:  
        subCol = 'tags'
        if myCode == '=': return
                 
    if myCode not in zPage[subCol]: 
        zPage[subCol].append( myCode )


def getTag(item):
    """
    El tag es el primer elemento de la linea ( separado por un espacio )
    se comparara siempre en mayusculas
    """

    if len(item) == 0 or item[0] not in ( NOTE_MARK, TAG_MARK ) :
        return ''

    return  (item.split() or [''])[0].strip().upper()


def doDotFile(  zPage ): 
    """Creacion del archivo dot 
    """


    zPage['tags'].sort()
    zPage['links'].sort()
    zPage['codes'].sort()

    pageName = sluglify( zPage['name'] )

    masterPageIx = 'digraph {rankdir=LR\n\n//sources\n'
    masterPageIx += 'node [shape=component, width=0, height=0, concentrate=true]\n'
    masterPageIx += '\t{0} \t[label="{1}"]\n'.format( pageName, pageName  )

    masterPageIx += '\n\n//tags\nnode [shape=box,width=0, height=0, concentrate=true]\n\n'
    for myTag in zPage['tags']:
        masterPageIx += '\t{0} \t[label="{1}"]\n'.format( myTag, myTag  )

    masterPageIx += '\n\n'
    for myTag in zPage['tags']:
        masterPageIx += '\t{0} -> {1}\n'.format( pageName, myTag )


    masterPageIx += '\n\n//QdaLinks\nnode [style=rounded, width=0, height=0, concentrate=true]\n'
    for myTag in zPage['codes']:
        masterPageIx += '\t{0} \t[label="{1}"]\n'.format( myTag, myTag  )

    masterPageIx += '\n\n'
    for myLink in zPage['links']:
        masterPageIx += '\t{0}\n'.format( myLink  )

    masterPageIx += '}\n'

    return masterPageIx


def doViewDotFile( pageName, folder, masterPageIx ): 
    """Crea el archivo fisico, el grafico y  abre xdot 
    """
    # Crea el archivo 
    import os 
    try:
        os.mkdir( unicode( folder ))
    except OSError: pass 

    fileNameDot =  '{0}/{1}'.format( folder, 'mapdoc.dot' ) 

    outfile = open(fileNameDot, "w")
    outfile.write( masterPageIx )
    outfile.close()

    # Genera el grafico
    try:
        import pygraphviz
        fileNamePng =  '{0}/{1}'.format( folder, 'mapdoc.png' ) 
 
        graph = pygraphviz.AGraph( fileNameDot )
        graph.layout( prog= 'dot' )
        graph.draw( fileNamePng, format ='png')
 
    except ImportError:
        pass

    # Abre el archivo 
    import subprocess 
    subprocess.Popen(["xdot", fileNameDot ])

