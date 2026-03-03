from rapidfuzz import process

class FuzzyMatcher:
    def __init__(self, vocab):
        self.vocab=[v.lower() for v in vocab]

    def correct(self, query, threshold=92):
        words=query.lower().split()
        corrected=[]

        for w in words:

            if w in self.vocab:
                corrected.append(w)
                continue

            match, score, _=process.extractOne(w,self.vocab)

            if score>=threshold and len(match.split())==1:
                corrected.append(match)
            else:
                corrected.append(w)

        return " ".join(corrected)