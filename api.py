from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from main import pipeline, format_context_for_llm
from rag.query_parser import *
from rag.res_llm import get_resp

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading RAG pipeline...")
retriever_obj, fuzzy_matcher, kg_retriever, entity_text_map = pipeline()
print("RAG Loaded!")

class Query(BaseModel):
    question: str


@app.post("/ask")
def ask_question(query: Query):

    question = query.question

    corrected = fuzzy_matcher.correct(question)

    entity = extract_entity(question, entity_text_map.keys())
    operator = extract_operator(corrected)
    number = get_capacity(corrected)
    range_vals = extract_range(corrected)
    wbody_types = extract_type(corrected)

    type_filter=None
    if isinstance(wbody_types,list) and len(wbody_types)==1:
        type_filter=wbody_types[0]

    if range_vals:
        context = capacity_filter(entity, operator, entity_text_map, range_vals_given=range_vals)

    elif operator:
        filtered_map = entity_text_map

        if type_filter:
            filtered_map={k:v for k,v in entity_text_map.items() if type_filter in v.lower()}

        context = capacity_filter(entity, operator, filtered_map, number=number)

        if not context:
            return {"answer":"No entities match the criteria"}

        context=format_context_for_llm(context)
        answer=get_resp(context,corrected)

        return {"answer":answer}

    kg_entities = kg_retriever.dynamic_search(corrected)

    context=[]

    for entity in kg_entities:
        if entity in entity_text_map:
            context.append(entity_text_map[entity])

    if not context:
        return {"answer":"No relevant data found"}

    context=format_context_for_llm(context)

    answer=get_resp(context, corrected)

    return {"answer":answer}