from rag.extract import extract_csv
from rag.embed import embedder
from rag.vectordb import vectordatabase
from rag.retrieve_info import retriever
from rag.res_llm import get_resp
from rag.entity_store import build_entity_vocab
from rag.fuzzy import FuzzyMatcher

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
    vocab=build_entity_vocab("data/water_bodies_data.csv")
    fuzzy_matcher=FuzzyMatcher(vocab)

    retriever_obj=retriever(vectdb, embedder_obj, fuzzy_matcher)

    return retriever_obj

    


def main():
    

    print("Initializing RAG GIS chatbot...\n")
    retriever_obj=pipeline()

    print("\nASK UR QUERIES!! \nType 'exit' to quit.\n")

    while True:
        question=input("USER: ")
        if question.lower()=="exit":
            print("BBYE!")
            break

        context=retriever_obj.retrieve(question)
        answer=get_resp(context,question)
        print("\nBot:",answer,"\n")

if __name__ == "__main__":
    main()