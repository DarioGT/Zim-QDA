'''
Created on Mar 13, 2015

@author: dario
'''

from zim.notebook import Path
from qdaSettings import NOTE_AUTOTITLE, sluglify


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
        self.idPage = self.ui.page.id 


    def do_ExportMapDoc(self):
        """ Exporta el mapa del documento 

        Por cada codigo genera las fuentes con formato record y label
        Genera una lista de codigos con su label
        genera la conexion de cada autor con los codigos
        si existen jerarquias ( listas separadas por , ) las presenta encadendas
        cuando hay conceptos jerarquizados no deberia vincularlos a la fuente
        """

        masterPath = self.plugin.preferences['namespace']

        # La idea es q sea por fuente en la idenxacion del documento                  
        sOrder = 'source, tag, description'
        sWhere = 'source = {0}'.format( self.idPage )

        mySource = ''
        myTag = ''
        myCode = ''
        zPages = {}

        for row in self.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):
            path = self.plugin.get_path(row)
            if path is None: continue

            #  description  ( elimina los comentarios : ... )
            tag = row['tag'].decode('utf-8').strip() 
            code = row['description'].decode('utf-8').split(':')[0].strip() 
            source = path.name 

            # Solo la marca, por ejemplo Keywords 
            if len (code) == 0: 
                continue

            # Break by Source ( normalmente 1 sola )
            if source != mySource:
                mySource = source
                myTag = ''
                myCode = ''

                # Agrega solo el basename 
                zPages[ mySource ] = { 'name' : sluglify( source ),  'tags' : [], 'links' : [] }

            # Break by Tag
            if tag != myTag:
                myTag = tag
                # No agrega el = ; es simplemente parte de la jerarquia 
                if myTag != '=': 
                    zPages[ mySoruce ][ 'tags'].append( myTag )

            if code == myCode:
                continue 

            myCode = code

            # Separa las relaciones directas al tag 
            myLinks = []
            myLinksA = [ j.strip() for j in code.split(';') ]
            for linkA in myLinksA:

                # Separa los conceptos jerarquicos 
                linkB = [ j.strip() for j in linkA.split(',') ]
                for i in range(0, len (linkB) - 1):
                    code = linkB[ i ]

                    # Split a primer nivel Debe tener un tag 
                    if '-' in code and i == 0  : 
                        myLinksB = [ j.strip() for j in code.split(',') ] 
                        for codeB in myLinksB :
                            addMapLink( myTag, codeB, myLinks )

                    # Tiene q dividir el ultimo nodo 
                    elif '-' in code and i == (len (linkB) - 1)   : 
                        myLinksB = [ j.strip() for j in code.split(',') ] 
                        for codeB in myLinksB :
                            addMapLink( myTag, codeB, myLinks )

                    # Primer nivel con tag 
                    if i == 0 and myTag != '=': 
                        addMapLink ( myTag , code, myLinks )

                    # Primer nivel sin tag, no hace nada pues se hara con base en el tag anterior 
                    elif i == 0 and myTag == '=': 
                        continue 

                    # Caso normal de un link q debe encadenarse con el nivel anterior 
                    elif i > 0  : 
                        codeB = linkB[ i - 1 ]
                        addMapLink ( codeB , code, myLinks )


            #  Agrega los links a la pagina 
            zPages[ mySource ][ 'links'].append( myLinks )


        # ============   Ya tiene la estructura de control 
        pageName = ':{0}:{1}'.format(masterPath, prefixPage) 
        self.plugin.ui.append_text_to_page( pageName , '======== {0} =========\n\n'.format( prefixPage  ) )


        masterPageIx = ''
        for zPage in zPages:
            zPage = zPages[ tag ]

            

            masterPageIx += 'digraph {rankdir=LR\n\n//sources\n'
            masterPageIx += 'node [shape=box,shape=box, width=0, height=0, concentrate=true]\n\n'

            zPage['tags']

            masterPageIx += '//tags\nnode [style=rounded]\n\n'

            for source in zPage['tags']:
                masterPageIx += '\t{0} \t[label="{0}"]\n'.format( source, source )


            masterPageIx += '\n//QdaLinks\nnode [shape=oval,width=0, height=0, concentrate=true]\n'
            for myLink in zPage['links']:
                masterPageIx += '\t{0}\n'.format( myLink  )

            masterPageIx += '}\n'

        # get_attachments_dir
        
def addMapLink ( myCode1, myCode2, myLinks   ): 

    myLink = '{0} -> {1}'.format( sluglify( myCode1 ), sluglify(myCode2))
    if myLink not in myLinks: 
        myLinks.append( myLink )
