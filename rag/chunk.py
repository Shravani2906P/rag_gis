import pandas as pd

def extract_csv(csv_path: str, group_size=4, overlap=1):
    df=pd.read_csv(csv_path).fillna("unknown")

    records=[]

    for _, row in df.iterrows():

        records.append(
            f"{row['Village']} is a {row['Activity']} located in {row['District']} "
            f"at coordinates ({row['Latitude']}, {row['Longitude']}). "
            f"Area: {row['Ar']} sqm, Length: {row['Length']} m, Depth: {row['Depth']} m."
        )

    chunks=[]

    i=0
    while i<len(records):
        chunks.append(" ".join(records[i:i+group_size]))
        i+=group_size-overlap

    return chunks