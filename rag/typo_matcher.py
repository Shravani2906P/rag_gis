from rapidfuzz import process

class FuzzyMatcher:
    def __init__(self, vocab):
        self.vocab=vocab

    def correct(self, query, threshold=80):
        words=query.lower().split()
        corrected=[]

        for w in words:
            match, score, _=process.extractOne(w,self.vocab)

            if score>=threshold:
                corrected.append(match)
            else:
                corrected.append(w)

        return " ".join(corrected)