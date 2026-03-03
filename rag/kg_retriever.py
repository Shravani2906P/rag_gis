class KGRetriever:

    def __init__(self, triples, embedder_obj):
        self.triples=triples
        self.embedder=embedder_obj

        self.graph={}
        self.reverse_graph={}
        self.nodes=set()

        self.capacity_map={}
        self.type_map={}
        self.purpose_map={}

        for s,r,o in triples:
            s=s.lower()
            o=o.lower()

            self.graph.setdefault(s,[]).append((r,o))
            self.reverse_graph.setdefault(o,[]).append((r,s))

            self.nodes.add(s)
            self.nodes.add(o)

            if r=="has_capacity":
                try:
                    value=int(o.split("m")[0])
                    self.capacity_map[s]=value
                except:
                    pass
            if r=="is_a":
                self.type_map[s]=o
            if r=="supports":
                self.purpose_map.setdefault(s,[]).append(o)    


        self.node_list=list(self.nodes)
        self.node_embeddings=self.embedder.embedtext(self.node_list)


    def semantic_node_match(self,query,top_k=5):

        query_embedding=self.embedder.embedtext([query])[0]

        scores=[]

        for i,node_emb in enumerate(self.node_embeddings):
            score=sum(a*b for a,b in zip(query_embedding,node_emb))
            scores.append((score,self.node_list[i]))

        scores.sort(reverse=True)

        return [node for _,node in scores[:top_k]]


    def generic_traverse(self,start_nodes,max_depth=2):

        visited=set()
        results=set()

        def dfs(node,depth):
            if depth>max_depth:
                return
            if node in visited:
                return

            visited.add(node)
            results.add(node)

            for r,neighbor in self.graph.get(node,[]):
                dfs(neighbor,depth+1)

            for r,neighbor in self.reverse_graph.get(node,[]):
                dfs(neighbor,depth+1)

        for node in start_nodes:
            dfs(node.lower(),0)

        return list(results)


    def dynamic_search(self,query):

        matched_nodes=self.semantic_node_match(query,top_k=5)

        results=self.generic_traverse(matched_nodes,max_depth=2)

        entity_nodes=[]

        for node in results:
            if node in self.graph:
                for r,o in self.graph[node]:
                    if r=="is_a":
                        entity_nodes.append(node)
                        break

        return entity_nodes