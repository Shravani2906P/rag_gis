from rag.embed import embedder
from rag.vectordb import vectordatabase
from rag.retrieve_info import retriever
from rag.res_llm import get_resp
from rag.extract import build_entity_vocab_from_csv,extract_csv
from rag.typo_matcher import FuzzyMatcher
from rag.kg_loader import load_kgraph
from rag.kg_retriever import KGRetriever

def pipeline():

    
    print("Extracting data from input csv!....")
    texts=extract_csv("data/water_bodies_data.csv")

    print("Chunking works!!")
    for i,chunk in enumerate(texts):
        print("\n---Chunk",i+1,"---")
        print(chunk)

   

    print("Building EMBEDDINGS....")
    embedder_obj=embedder()
    embeddings=embedder_obj.embedtext(texts)

    print("Embedding shape:", len(embeddings), "x", len(embeddings[0]))
    print("First embedding vector:\n", embeddings[0])
    print("Forming TEXT VECTORS.... ")
    vectdb=vectordatabase(dimension=len(embeddings[0]))
    vectdb.add(embeddings, texts)
    print("Vectors stored in FAISS:", vectdb.index.ntotal)

    print("Building entity vocabulary...")
    vocab=build_entity_vocab_from_csv("data/water_bodies_data.csv")
    fuzzy_matcher=FuzzyMatcher(vocab)

    retriever_obj=retriever(vectdb, embedder_obj, fuzzy_matcher)

    print("\nLoading Knowledge Graph...")
    triples=load_kgraph("rag/kgraph.json")
    kg_retriever=KGRetriever(triples)

    return retriever_obj,fuzzy_matcher,kg_retriever

    


def main():
    

    print("Initializing RAG GIS chatbot...\n")
    retriever_obj, fuzzy_matcher, kg_retriever=pipeline()

    print("\nASK UR QUERIES!! \nType 'exit' to quit.\n")

    while True:
        question=input("USER: ")
        if question.lower()=="exit":
            print("BBYE!")
            break

    #Applying typo correction    
        corrected=fuzzy_matcher.correct(question)
        print("\nOriginal Query :",question)
        print("Corrected Query:",corrected)
    #FAISS RETRIEVAL
        faiss_context=retriever_obj.retrieve(corrected)
    #KG RETRIEVAL    
        kg_context=kg_retriever.dynamic_search(corrected)
    #MERGING BOTH for best results    
        context=faiss_context+kg_context
        
        answer=get_resp(context,corrected)
        print("\nBot:",answer,"\n")
        # print("\n--- KG UNIT TEST ---")
        # print("Test irrigation:", kg_retriever.dynamic_search("irrigation"))
        # print("Test large:", kg_retriever.dynamic_search("large"))
        # print("Test small:", kg_retriever.dynamic_search("small"))
        # print("--------------------\n")

if __name__ == "__main__":
    main()