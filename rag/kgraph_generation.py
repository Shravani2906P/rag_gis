import pandas as pd

class kgraphbuilder:

    def __init__(self):
        self.triples = []

    def build(self, csv_path):

        df=pd.read_csv(csv_path).fillna("unknown")

        for _, row in df.iterrows():

            name=str(row['Village']).lower()
            type_=str(row['Activity']).lower()
            district=str(row['District']).lower()

            area=str(row['Ar'])
            length=str(row['Length'])
            depth=str(row['Depth'])

            #core relations
            self.triples.append((name, "is_a", type_))
            self.triples.append((name, "located_in", district))

        #  attributes
            self.triples.append((name, "has_area", area))
            self.triples.append((name, "has_length", length))
            self.triples.append((name, "has_depth", depth))

            #reverse relships
            self.triples.append((type_, "includes", name))
            self.triples.append((district, "contains", name))

            #cross relships
            self.triples.append((type_, "exists_in", district))
            self.triples.append((district, "has_type", type_))

        return self.triples