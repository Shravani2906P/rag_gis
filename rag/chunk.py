#used overlap based chunking currently, since took data directly from csv
import pandas as pd
def extract_csv(csv_path:str,group_size=4,overlap=1):
 df=pd.read_csv(csv_path).fillna("unknown")

 records=[]
 
 for _,row in df.iterrows():
  records.append(f"{row['name']} is a {row['type']} located in {row['district']} at coordinates ({row['latitude']}, {row['longitude']}). It has a capacity of {row['capacity']}. {row['description']}.")
 
 chunks=[]
 
 i=0
 while i<len(records):
  chunks.append(" ".join(records[i:i+group_size]))
  i+=group_size-overlap
 
 return chunks