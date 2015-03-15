

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
        
