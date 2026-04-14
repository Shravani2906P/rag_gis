from rapidfuzz import process, fuzz
import re


class FuzzyMatcher:

    def __init__(self, vocab):
        self.vocab=[v.lower() for v in vocab]

        self.common_words=[
            "water","body","bodies",
            "lake","lakes",
            "pond","ponds",
            "dam","dams",
            "anicut","anicuts",
            "tank","tanks",
            "reservoir","reservoirs",
            "canal","canals",
            "talab",
            "check","checkdam","check-dam",
            "percolation",
            "johad",
            "farm","pond",
            "list","give","show","find","all",
            "best","top","largest","smallest"
        ]

        self.stop_words=[
            "how","many","are","is","in","of","the","there",
            "what","which","where","with","and","a","an","to"
        ]

        self.full_vocab=list(set(self.vocab + self.common_words))

        self.short_map={
            "dms":"dams",
            "dm":"dam",
            "lks":"lakes",
            "lk":"lake",
            "rsrv":"reservoir",
            "anicuts":"anicut",
            "anicyts":"anicut",
            "anicutss":"anicut"
        }

  
    def normalize_word(self,w):
        w=re.sub(r'[^a-z]', '', w)

        if w.endswith("s") and len(w)>4:
            w=w[:-1]

        return w

    
    def correct(self,query):

        words=query.lower().split()
        corrected=[]

        for w in words:

            # keep numbers always
            if w.replace('.', '', 1).isdigit():
                corrected.append(w)
                continue

            w=self.normalize_word(w)

            if w in self.stop_words:
                corrected.append(w)
                continue

            if w in self.short_map:
                corrected.append(self.short_map[w])
                continue

            if w in self.full_vocab:
                corrected.append(w)
                continue

            if len(w)<=3:
                corrected.append(w)
                continue

            match=process.extractOne(w,self.full_vocab,scorer=fuzz.ratio)

            if match and match[1]>75:
                corrected.append(match[0])
            else:
                corrected.append(w)

        return " ".join(corrected)