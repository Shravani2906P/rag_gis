class QueryMapper:

    def map_query(self, query):

        query=query.lower()

        concepts=[]

        words=query.split()

        for w in words:
            concepts.append(w)

        return concepts