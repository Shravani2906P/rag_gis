from rag.embed import embedder
from rag.vectordb import vectordatabase
from rag.retrieve_info import retriever
from rag.res_llm import get_resp
from rag.extract import build_entity_vocab_from_csv,extract_csv
from rag.typo_matcher import FuzzyMatcher
from rag.kg_loader import load_kgraph
from rag.kg_retriever import KGRetriever
from rag.query_parser import extract_entity,extract_operator,capacity_filter,get_capacity,extract_type,extract_second_entity,detect_intent_of_ques,extract_range

def pipeline():

    
    print("Extracting data from input csv!....")
    texts=extract_csv("data/water_bodies_data.csv")

    entity_text_map={}
    for text in texts:
        name=text.split(" is a ")[0].lower()
        entity_text_map[name]=text

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
    kg_retriever=KGRetriever(triples,embedder_obj)

    return retriever_obj,fuzzy_matcher,kg_retriever,entity_text_map

    

def format_context_for_llm(context):

    formatted=[]

    for text in context:

        name=text.split(" is a ")[0]
        type_=text.split(" is a ")[1].split(" located")[0]
        coords=text.split("coordinates ")[1].split(")")[0]+")"
        capacity=text.split("capacity of ")[1].split(".")[0]
        purpose=text.split(".")[-2]
        formatted.append(f"{name} - {type_} - {coords} -  {capacity} - {purpose}")

    return formatted


def main():

    print("Initializing RAG GIS chatbot...\n")
    retriever_obj, fuzzy_matcher, kg_retriever,entity_text_map=pipeline()

    print("\nASK UR QUERIES!! \nType 'exit' to quit.\n")

    while True:
        question=input("USER: ")

        if question.lower()=="exit":
            print("BBYE!")
            break

        corrected=fuzzy_matcher.correct(question)

        print("\nOriginal Query :", question)
        print("Corrected Query:", corrected)

        entity=extract_entity(corrected,entity_text_map.keys())
        operator=extract_operator(corrected)
        number=get_capacity(corrected)
        type_filter=extract_type(corrected)
        range_vals=extract_range(corrected)

        print("Detected entity   : ",entity)
        print("Detected operator : ",operator)
        print("Detected number   : ",number)
        print("Detected type     : ",type_filter)

        if range_vals:
            context=capacity_filter(entity, operator, entity_text_map, range_vals_given=range_vals)

        elif operator:
            context=capacity_filter(entity, operator, entity_text_map, number=number)

            print("Filtered entities : ",context)

            if not context:
                print("\nBot: No entities match the given criteria :(\n")
                continue

            context=format_context_for_llm(context)

            answer=get_resp(context,corrected)
            print("\nBot: ",answer,"\n")
            continue

        # #kgraph based retrieval
        kg_entities=kg_retriever.dynamic_search(corrected)
        print("KG Entities:", kg_entities)

        #faiis based retrieval
        context=[]

        for entity in kg_entities:
           if entity in entity_text_map:
               context.append(entity_text_map[entity])

        print("FAISS Entities:", context)

        if not context:
            print("\nBot: No relevant data found.\n")
            continue
#using filtering if query is rank based
        if type_filter:
            context=[x for x in context if f"{type_filter.capitalize()}" in x]
        
        #checking for words like count, min,max as llm hallucinates from nums!!
        intent_of_ques=detect_intent_of_ques(corrected)
        context=format_context_for_llm(context)

        if intent_of_ques=="COUNT":
            count=len(context)
            print(f"Bot: There are {count} matching water bodies. Below are the details:\n")
            for i,it in enumerate(context,start=1):
                print(f"{i}. {it}")
            print()
            continue
        if intent_of_ques=="MAX":
            topmax=sorted(context,
                          key=lambda x:int(x.split(" - ")[3].split("M")[0]), reverse=True)[:3]
            answer=get_resp(topmax,corrected)
            print("\nBot: ",answer,"\n")
            continue   
        if intent_of_ques=="MIN":
            topmin=sorted(context,
                          key=lambda x:int(x.split(" - ")[3].split("M")[0]), reverse=False)[:3]
            answer=get_resp(topmin,corrected)
            print("\nBot: ",answer,"\n")
            continue   
        answer=get_resp(context, corrected)
        print("\nBot:", answer, "\n")
        # print("\n--- KG UNIT TEST ---")
        # print("Test irrigation:", kg_retriever.dynamic_search("irrigation"))
        # print("Test large:", kg_retriever.dynamic_search("large"))
        # print("Test small:", kg_retriever.dynamic_search("small"))
        # print("--------------------\n")

if __name__ == "__main__":
    main()