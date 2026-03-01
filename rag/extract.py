import pandas as pd

def extract_csv(csv_path: str):
    df=pd.read_csv(csv_path).fillna("unknown")

    extracted_texts=[]

    for _, row in df.iterrows():
        ex=(
            f"{row['name']} is a {row['type']} located in {row['district']} "
            f"at coordinates ({row['latitude']}, {row['longitude']}). "
            f"It has a capacity of {row['capacity']}. "
            f"{row['description']}"
        )
        extracted_texts.append(ex)

    return extracted_texts


def build_entity_vocab_from_csv(csv_path):
    df=pd.read_csv(csv_path).fillna("unknown")

    vocab=set()

    for _, row in df.iterrows():
        vocab.add(row['name'].lower())
        vocab.add(row['type'].lower())
        vocab.add(row['district'].lower())

    return list(vocab)