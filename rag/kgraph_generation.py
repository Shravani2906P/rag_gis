import pandas as pd
import re

class kgraphbuilder:

    def __init__(self):
        self.triples=[]

    def extract_purpose(self, desc):

        desc=desc.lower()

        if "irrigation" in desc:
            return "irrigation"
        if "drinking" in desc:
            return "drinking"
        if "recharge" in desc:
            return "groundwater recharge"
        if "rainwater" in desc:
            return "rainwater harvesting"
        if "ecosystem" in desc:
            return "ecosystem support"

        return None

    def build(self, csv_path):

        df=pd.read_csv(csv_path).fillna("unknown")

        for _, row in df.iterrows():

            name=row['name']
            type_=row['type']
            district=row['district']
            capacity=row['capacity']
            desc=row['description']

            purpose=self.extract_purpose(desc)

            #node relships
            self.triples.append((name, "is_a", type_))
            self.triples.append((name, "located_in", district))
            self.triples.append((name, "has_capacity", capacity))

            #reverse reships
            self.triples.append((type_, "includes", name))
            self.triples.append((district, "contains", name))
            self.triples.append((capacity, "capacity_of", name))

            #cross relships
            self.triples.append((type_, "exists_in", district))
            self.triples.append((district, "has_type", type_))

            #purpose relships
            if purpose:
                self.triples.append((name, "supports", purpose))
                self.triples.append((purpose, "supported_by", name))
                self.triples.append((district, "benefits_from", purpose))
                self.triples.append((purpose, "occurs_in", district))

        return self.triples