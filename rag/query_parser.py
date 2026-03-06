import re


def extract_entity(query, entities):

    query=query.lower()

    for e in entities:
        if e in query:
            return e

    return None

def extract_second_entity(query, entities, first_entity):

    for e in entities:
        if e in query and e!=first_entity:
            return e

    return None

def extract_type(query):

    types=["lake","dam","reservoir","pond","barrage"]

    for t in types:
        if t in query.lower():
            return t

    return None




def extract_operator(query):

    query=query.lower()

    if "greater than or equal" in query or "at least" in query:
        return ">="

    if "less than or equal" in query or "at most" in query:
        return "<="

    if ("greater than" in query or "larger than" in query or "bigger than" or "above" in query):
        return ">"

    if ("less than" in query or "smaller than" or "below" in query):
        return "<"

    if "equal to" in query or "same as" in query:
        return "="

    return None


def get_capacity(text):

    m=re.search(r'(\d+)\s*m',text.lower())

    if m:
        return int(m.group(1))

    return 0

def capacity_filter(entity, operator, entity_text_map,number=None):
    if entity:
        ref_capacity=get_capacity(entity_text_map[entity])
    else:
        ref_capacity=number   
    

    results=[]

    for name, text in entity_text_map.items():

        cap=get_capacity(text)

        if operator==">" and cap>ref_capacity:
            results.append((cap,text))

        elif operator=="<" and cap<ref_capacity:
            results.append((cap,text))

        elif operator=="=" and cap==ref_capacity:
            results.append((cap,text))

    #sorted in desc order
    results.sort(reverse=True, key=lambda x:x[0])

    return [text for cap,text in results]
