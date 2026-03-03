import re

class KGRetriever:

    SIZE_SYNONYMS={
        "large":[
            "large","big","huge","massive","major",
            "high","high-capacity","heavy","significant",
            "substantial","extensive","grand"
        ],
        "medium":[
            "medium","moderate","mid","mid-size",
            "average","standard","normal"
        ],
        "small":[
            "small","minor","low","low-capacity",
            "limited","tiny","mini","compact"
        ]
    }

    def __init__(self,triples):
        self.triples=triples
        self.graph={}
        self.reverse_graph={}
        self.capacity_class={}
        self.size_lookup={}

        for s,r,o in triples:
            self.graph.setdefault(s.lower(),[]).append((r,o.lower()))
            self.reverse_graph.setdefault(o.lower(),[]).append((r,s.lower()))

            if r=="has_capacity":
                try:
                    value=int(o.lower().split("m")[0])
                    if value>=250:
                        self.capacity_class[s.lower()]="large"
                    elif value>=100:
                        self.capacity_class[s.lower()]="medium"
                    else:
                        self.capacity_class[s.lower()]="small"
                except:
                    pass

        for size_class,synonyms in self.SIZE_SYNONYMS.items():
            for word in synonyms:
                self.size_lookup[word]=size_class


    def extract_query_nodes(self,query):
        words=re.findall(r'\b\w+\b',query.lower())
        nodes=[]
        for word in words:
            if word in self.graph or word in self.reverse_graph:
                nodes.append(word)
        return nodes


    def detect_size(self,query):
        words=re.findall(r'\b\w+\b',query.lower())
        for word in words:
            if word in self.size_lookup:
                return self.size_lookup[word]
        return None


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
        size_filter=self.detect_size(query)
        start_nodes=self.extract_query_nodes(query)

        if not start_nodes and not size_filter:
            return []
        
        if start_nodes:
            results=self.generic_traverse(start_nodes,max_depth=2)
        else:
            results=list(self.capacity_class.keys())

        entity_nodes=[]
        for node in results:
            if node in self.capacity_class:
                if size_filter:
                    if self.capacity_class[node]==size_filter:
                        entity_nodes.append(node)
                else:
                    entity_nodes.append(node)

        return entity_nodes