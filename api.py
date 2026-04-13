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

    question=query.question

    corrected=fuzzy_matcher.correct(question)
    corrected=re.sub(r'\b(storage|tank|tanks|storage-tanks)\b','',corrected.lower())
    corrected=" ".join(dict.fromkeys(corrected.split()))

    entity=extract_entity(question, entity_text_map.keys())
    operator=extract_operator(corrected)
    number=get_capacity(corrected)
    range_vals=extract_range(corrected)
    wbody_types=extract_type(corrected)

    type_filter=None
    if isinstance(wbody_types, list) and len(wbody_types) == 1:
        type_filter = wbody_types[0]

    #cross type queries
    if isinstance(wbody_types, list) and len(wbody_types) == 2 and operator:
        type1, type2 = None, None

        if "than" in corrected:
            parts=corrected.split("than")
            left, right = parts[0], parts[1]

            for t in wbody_types:
                if t in left:
                    type1 = t
                if t in right:
                    type2 = t
        else:
            type1, type2 = wbody_types

        context = cross_type_compare(type1, type2, operator, entity_text_map)

        if not context:
            return {"answer": "No entities satisfy the comparison."}

        context = format_context_for_llm(context)
        answer = get_resp(context, corrected)
        return {"answer": answer}

    # range detector
    if range_vals:
        context = capacity_filter(entity, operator, entity_text_map, range_vals_given=range_vals)

        if not context:
            return {"answer": "No entities match the criteria"}

        context = format_context_for_llm(context)
        answer = get_resp(context, corrected)
        return {"answer": answer}

    # opertor detector
    elif operator:
        filtered_map = entity_text_map

        if type_filter:
            filtered_map = {
                k: v for k, v in entity_text_map.items()
                if type_filter in v.lower()
            }

        context = capacity_filter(entity, operator, filtered_map, number=number)

        if not context:
            return {"answer": "No entities match the criteria"}

        context = format_context_for_llm(context)
        answer = get_resp(context, "Explain the following water bodies that match the user's query.")
        return {"answer": answer}

    #kg retrveal
    kg_entities = kg_retriever.dynamic_search(corrected)

    context = []
    for entity in kg_entities:
        if entity in entity_text_map:
            context.append(entity_text_map[entity])

    if not context:
        return {"answer": "No relevant data found"}

    if type_filter:
        context = [x for x in context if type_filter in x.lower()]

 #intent detection
    intent=detect_intent_of_ques(corrected)

    context=format_context_for_llm(context)

    if intent=="COUNT":
        return {
            "answer": f"There are {len(context)} matching water bodies.",
            "data": context
        }

    if intent=="MAX":
        topmax = sorted(
            context,
            key=lambda x: int(x.split(" - ")[3].split("M")[0]),
            reverse=True
        )[:5]

        answer=get_resp(topmax, corrected)
        return {"answer": answer}

    if intent=="MIN":
        topmin=sorted(
            context,
            key=lambda x: int(x.split(" - ")[3].split("M")[0])
        )[:5]

        answer=get_resp(topmin, corrected)
        return {"answer": answer}

  
    answer=get_resp(context, corrected)
    return {"answer": answer}