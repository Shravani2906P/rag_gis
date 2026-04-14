import re

#extract entity
def extract_entity(query, entities):

    query=query.lower()

    for e in entities:
        if f" {e} " in f" {query} ":
            return e

    return None


def extract_second_entity(query, entities, first_entity):

    query = query.lower()

    for e in entities:
        if e in query and e != first_entity:
            return e

    return None


#type extraction
def extract_type(query):

    types = [
        "anicut",
        "percolation tank",
        "talab",
        "whs",
        "nalah"
    ]

    found=[]
    query=query.lower()

    for t in types:
        if t in query or t + "s" in query:
            found.append(t)

    return found


#extract op
def extract_operator(query):

    query=query.lower()

    if any(w in query for w in ["greater than or equal", "at least"]):
        return ">="

    if any(w in query for w in ["less than or equal", "at most"]):
        return "<="

    if any(w in query for w in ["greater than", "larger than", "bigger than", "above"]):
        return ">"

    if any(w in query for w in ["less than", "smaller than", "below"]):
        return "<"

    if any(w in query for w in ["equal to", "same as", "equal"]):
        return "="

    return None


#extract num
def extract_number(query):

    nums=re.findall(r'\d+', query)
    return float(nums[0]) if nums else None


def extract_range(query):

    nums=re.findall(r'(\d+)', query)

    if len(nums)>=2:
        low=float(nums[0])
        high=float(nums[1])
        return low, high

    return None


#field detectin
def detect_field(query):

    q=query.lower()

    if "depth" in q or "deep" in q:
        return "depth"

    if "length" in q or "long" in q:
        return "length"

    # default = area
    return "area"


#parse area
def get_area(text):

    try:
        return float(text.split("area of ")[1].split(" square")[0])
    except:
        return None



def cross_type_compare(type1, type2, operator, entity_text_map):

    type1_items=[]
    type2_items=[]

    for text in entity_text_map.values():

        if f"is a {type1}" in text.lower():
            type1_items.append(text)

        if f"is a {type2}" in text.lower():
            type2_items.append(text)

    results=[]

    for t1 in type1_items:

        a1=get_area(t1)
        if a1 is None:
            continue

        for t2 in type2_items:

            a2=get_area(t2)
            if a2 is None:
                continue

            if operator == ">" and a1 > a2:
                results.append(t1)
                break

            if operator == "<" and a1 < a2:
                results.append(t1)
                break

    return results


# intent detection
def detect_intent_of_ques(query):

    q = query.lower()

    count_words = ["how many", "count", "number of", "total", "in total"]
    max_words = ["maximum", "highest", "largest", "top", "best"]
    min_words = ["smallest", "minimum", "lowest"]

    for w in count_words:
        if w in q:
            return "COUNT"

    for w in max_words:
        if w in q:
            return "MAX"

    for w in min_words:
        if w in q:
            return "MIN"

    return "LIST"