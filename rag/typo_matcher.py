from rapidfuzz import process,fuzz

class FuzzyMatcher:
    def __init__(self, vocab):

        self.vocab=vocab

        self.common_words=[
            "water","bodies","body","lake","pond","dam","reservoir","capacity","larger","greater","than","above","below","list","give","show","find","smaller","medium","average"
        ]
        self.full_vocab=list(set(self.vocab+self.common_words))

    def correct(self,query):
        words=query.lower().split()
        corrected=[]

        for w in words:

            if w in self.vocab:
                corrected.append(w)
                continue

            match=process.extractOne(
                w,
                self.full_vocab,
                scorer=fuzz.ratio
            )

            if match and match[1]>80:
                corrected.append(match[0])
            else:
                corrected.append(w)

        return " ".join(corrected)