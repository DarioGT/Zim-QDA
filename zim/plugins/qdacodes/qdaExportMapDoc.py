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
        self.page = plugin.ui.page   
        self.path = self.ui.notebook.index.lookup_path(self.page )
        self.pageId = self.path.id    


    def do_ExportMapDoc(self):
        """ Exporta el mapa del documento  ( ver wiki )
        """

        # La idea es q sea por fuente en la idenxacion del documento                  
        sOrder = 'source, tag, description'
        sWhere = 'tag <> \'{1}\' and source = {0}'.format( self.pageId, 'QDATITLE' )

        pageName = self.path.basename
        zPage = {  'tags' : [], 'links' : [] }

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
                        tag2 = tag2[1:].strip() 
                        linkA = linkA[len(tag2)+1:].strip()
                else: tag2 = tag0 

                if len( tag2 ) == 0 : tag2 = tag0
                myTag = sluglify(tag2)

                if tag2 != '=' and not myTag in zPage[ 'tags'] :
                    zPage[ 'tags'].append(myTag)

                doCodeRelations( zPage, linkA, tag2, myTag )

        doDotFile( self.path.basename, self.page.folder, zPage )


def doCodeRelations( zPage, linkA, tag, myTag ):

    # Separa los conceptos jerarquicos 
    linkB = [ j.strip() for j in linkA.split(SEP_CODE) ]
    for i in range(0, len(linkB)):
        code = linkB[ i ]

        # Split a primer nivel Debe tener un tag 
        if SEPLISTA in code and i == 0  : 
            myCodeB = [ j.strip() for j in code.split(SEPLISTA) ] 
            for codeB in myCodeB :
                addMapLink( myTag, codeB, zPage )

        # Tiene q dividir el ultimo nodo 
        elif SEPLISTA in code and i == (len (linkB) - 1)   : 
            myCodeB = [ j.strip() for j in code.split(SEPLISTA) ] 
            codeA = linkB[ i - 1 ]
            for codeB in myCodeB :
                addMapLink( codeA, codeB, zPage )

        # Primer nivel con tag 
        elif i == 0 and tag != '=': 
            addMapLink ( myTag , code, zPage )

        # Primer nivel sin tag, no hace nada pues se hara con base en el tag anterior 
        elif i == 0 and tag == '=': 
            continue 

        # Caso normal de un link q debe encadenarse con el nivel anterior 
        elif i > 0  : 
            codeB = linkB[ i - 1 ]
            addMapLink ( codeB , code, zPage )

def addMapLink ( myCode1, myCode2, zPage   ): 

    myLink = '{0} -> {1}'.format( sluglify( myCode1 ), sluglify(myCode2))
    if myLink not in zPage.get( 'links' ): 
        zPage.get('links').append( myLink )


def getTag(item):
    """
    El tag es el primer elemento de la linea ( separado por un espacio )
    se comparara siempre en mayusculas
    """

    if not item[0] in ( NOTE_MARK, TAG_MARK ) :
        return ''

    return  (item.split() or [''])[0].strip().upper()


def doDotFile( pageName, folder, zPage ): 
    """Creacion del archivo dot 
    """

    pageName = sluglify( pageName )

    masterPageIx = 'digraph {rankdir=LR\n\n//sources\n'
    masterPageIx += 'node [shape=box,shape=box, width=0, height=0, concentrate=true]\n\t'
    masterPageIx +=  pageName 

    masterPageIx += '\n\n//tags\nnode [style=rounded]\n\n'

    for myTag in zPage['tags']:
        masterPageIx += '\t{0} -> {1}\n'.format( pageName, myTag )

    masterPageIx += '\n\n//QdaLinks\nnode [shape=oval,width=0, height=0, concentrate=true]\n'
    for myLink in zPage['links']:
        masterPageIx += '\t{0}\n'.format( myLink  )

    masterPageIx += '}\n'

    # Crea el archivo 
    import os 
    try:
        os.mkdir( unicode( folder ))
    except OSError: pass 

    fileNameDot =  '{0}/{1}'.format( folder, 'mapdoc.dot' ) 

    outfile = open(fileNameDot, "w")
    outfile.write( masterPageIx )
    outfile.close()

    try:
        import pygraphviz
        fileNamePng =  '{0}/{1}'.format( folder, 'mapdoc.png' ) 
 
        graph = pygraphviz.AGraph( fileNameDot )
        graph.layout( prog= 'dot' )
        graph.draw( fileNamePng, format ='png')
 
    except ImportError:
        pass

    import subprocess 
    subprocess.Popen(["xdot", fileNameDot ])

    # dot -Tpng mapdoc.dot > mapdoc.png
