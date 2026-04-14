import pandas as pd

def extract_csv(csv_path: str):
    df=pd.read_csv(csv_path).fillna("unknown")

    texts=[]

    for _, row in df.iterrows():

        name=str(row['Village'])
        type_=str(row['Activity'])
        district=str(row['District'])

        lat=row['Latitude']
        lon=row['Longitude']

        area=row['Ar']
        length=row['Length']
        depth=row['Depth']

        text=(
            f"{name} is a {type_} located in {district} "
            f"at coordinates ({lat}, {lon}). "
            f"It has an area of {area} square meters, "
            f"length of {length} meters, "
            f"and depth of {depth} meters."
        )

        texts.append(text)

    return texts


def build_entity_vocab_from_csv(csv_path):
    df=pd.read_csv(csv_path).fillna("unknown")

    vocab=set()

    for _, row in df.iterrows():
        vocab.add(str(row['Village']).lower())
        vocab.add(str(row['Activity']).lower())
        vocab.add(str(row['District']).lower())

    return list(vocab)