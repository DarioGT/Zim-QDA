'''
Created on Mar 13, 2015

@author: dario
'''

from zim.notebook import Path
from qdaSettings import sluglify
from qdaSettings import NOTE_MARK, NOTE_AUTOTITLE

TAG_MARK = ""


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
        self.idPage = 20   #lookup_path  plugin.ui.page  


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
        sWhere = 'tag <> \'{1}\' and source = {0}'.format( self.idPage, 'QDATITLE' )

        SEPLISTA = '-'
        SEP__TAG = ';'
        SEP_CODE = ','

        mySource = ''
        zPages = {}

        for row in self.plugin.list_codes(parent=None, orderBy=sOrder, whereStmt=sWhere):
            path = self.plugin.get_path(row)
            if path is None: continue

            # Break by Source ( normalmente 1 sola )
            source = path.name 
            if source != mySource:
                mySource = source
                myCode = ''

                # Agrega solo el basename 
                zPages[ mySource ] = { 'name' : sluglify( source ),  'tags' : [], 'links' : [] }

            # Elimina los comentarios 
            code = row['description'].decode('utf-8').split(':')[0].strip() 
            if len (code) == 0 or code == myCode: continue
            myCode = code

            # No agrega el = ; es simplemente parte de la jerarquia 
            tag = row['tag'].decode('utf-8').strip() 

            # Separa las relaciones directas al tag 
            myLinksA = [ j.strip() for j in code.split(SEP__TAG) ]
            for iTag  in range(0, len(myLinksA)):
                linkA = myLinksA[ iTag ] 

                if iTag > 0: 
                    tag = getTag( linkA )
                    if len( tag ) > 1 : 
                        tag = tag[1:] 
                        linkA = linkA[len(tag)+1:].strip()

                myTag = sluglify(tag)
                if tag != '=' and not myTag in zPages[ mySource ][ 'tags'] :
                    zPages[ mySource ][ 'tags'].append(myTag)

                # Separa los conceptos jerarquicos 
                linkB = [ j.strip() for j in linkA.split(SEP_CODE) ]
                for i in range(0, len(linkB)):
                    code = linkB[ i ]

                    # Split a primer nivel Debe tener un tag 
                    if SEPLISTA in code and i == 0  : 
                        myLinksB = [ j.strip() for j in code.split(SEPLISTA) ] 
                        for codeB in myLinksB :
                            addMapLink( myTag, codeB, zPages[ mySource ] )

                    # Tiene q dividir el ultimo nodo 
                    elif SEPLISTA in code and i == (len (linkB) - 1)   : 
                        myLinksB = [ j.strip() for j in code.split(SEPLISTA) ] 
                        codeA = linkB[ i - 1 ]
                        for codeB in myLinksB :
                            addMapLink( codeA, codeB, zPages[ mySource ] )

                    # Primer nivel con tag 
                    elif i == 0 and tag != '=': 
                        addMapLink ( myTag , code, zPages[ mySource ] )

                    # Primer nivel sin tag, no hace nada pues se hara con base en el tag anterior 
                    elif i == 0 and tag == '=': 
                        continue 

                    # Caso normal de un link q debe encadenarse con el nivel anterior 
                    elif i > 0  : 
                        codeB = linkB[ i - 1 ]
                        addMapLink ( codeB , code, zPages[ mySource ] )



        # ============   Ya tiene la estructura de control 
        pageName = 'xx' 
#         prefixPage = 'xxx'
#         pageName = ':{0}:{1}'.format(masterPath, prefixPage) 
#         self.plugin.ui.append_text_to_page( pageName , '======== {0} =========\n\n'.format( prefixPage  ) )


#         masterPageIx = ''
#         for zPage in zPages:

#             masterPageIx += 'digraph {rankdir=LR\n\n//sources\n'
#             masterPageIx += 'node [shape=box,shape=box, width=0, height=0, concentrate=true]\n\n'
# #             masterPageIx += zPage( 'name' )

#             masterPageIx += '//tags\nnode [style=rounded]\n\n'

#             for myTag in zPage['tags']:
#                 masterPageIx += '\t{0} \t[label="{0}"]\n'.format( myTag, myTag )


#             masterPageIx += '\n//QdaLinks\nnode [shape=oval,width=0, height=0, concentrate=true]\n'
#             for myLink in zPage['links']:
#                 masterPageIx += '\t{0}\n'.format( myLink  )

#             masterPageIx += '}\n'

        # get_attachments_dir
        
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

