import pandas as pd

def build_entity_vocab(csv_path):
    df=pd.read_csv(csv_path).fillna("unknown")

    vocab=set()

    for _, row in df.iterrows():
        vocab.add(row['name'].lower())
        vocab.add(row['type'].lower())
        vocab.add(row['district'].lower())

    return list(vocab)