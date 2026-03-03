class retriever:
    def __init__(self,vectordb,embedder,fuzzy_matcher):
        self.vectordb=vectordb
        self.embedder=embedder
        self.fuzzy=fuzzy_matcher

    def retrieve(self, ques, k=8):

        #original query
        original_embed=self.embedder.embedtext([ques])

        #best corrected query
        corrected=self.fuzzy.correct(ques)
        corrected_embed=self.embedder.embedtext([corrected])

        #searchin using both
        res1=self.vectordb.search(original_embed, k)
        res2=self.vectordb.search(corrected_embed, k)

        return list(set(res1+res2))