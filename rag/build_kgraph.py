import json
from kgraph_generation import kgraphbuilder

builder=kgraphbuilder()
triples=builder.build("data/govt.csv")

with open("rag/kgraph.json", "w") as f:
    json.dump(triples, f)

print("Knowledge graph built n saved.")