import re


def extract_entity(query, entities):

    query=query.lower()

    for e in entities:
        if f" {e} " in f" {query} ":
            return e

    return None

def extract_second_entity(query, entities, first_entity):

    for e in entities:
        if e in query and e!=first_entity:
            return e

    return None

def extract_type(query):

    types=["lake","dam","check dam","reservoir","pond","barrage",]
    found=[]
    query=query.lower()
    for t in types:
        if t in query or t+"s" in query:
            found.append(t)

    return found

#cross type comparisons, like list dams smller than reservoirs
def cross_type_compare(type1,type2,operator,entity_text_map):

    type1_items=[]
    type2_items=[]

    for text in entity_text_map.values():

        if f"is a {type1.capitalize()}" in text:
            type1_items.append(text)

        if f"is a {type2.capitalize()}" in text:
            type2_items.append(text)

    results=[]

    for t1 in type1_items:

        cap1=get_capacity(t1)

        if cap1 is None:
            continue

        for t2 in type2_items:

            cap2=get_capacity(t2)

            if cap2 is None:
                continue

            if operator=="<" and cap1<cap2:
                results.append(t1)
                break

            if operator==">" and cap1>cap2:
                results.append(t1)
                break

    return results

def extract_operator(query):

    query=query.lower()

    if any(word in query for word in ["greater than or equal","at least"]):
        return ">="

    if any(word in query for word in ["less than or equal","at most"]):
        return "<="

    if any(word in query for word in ["greater than", "larger than","bigger than","above"]):
        return ">"

    if any(word in query for word in ["less than","smaller than","below"]):
        return "<"

    if any(word in query for word in ["equal to","same as","same","equal"]):
        return "="

    return None


def get_capacity(text):

    m=re.search(r'capacity of\s*(\d+)', text.lower())

    if m:
        return int(m.group(1))

    return None

def capacity_filter(entity, operator, entity_text_map,number=None,range_vals_given=None):
    if entity:
        ref_capacity=get_capacity(entity_text_map[entity])
    else:
        ref_capacity=number   

    if ref_capacity is None and not range_vals_given:
        return []    

    results=[]

    for name, text in entity_text_map.items():

        cap=get_capacity(text)

        if cap is None:
            continue

        if range_vals_given:
            low,high=range_vals_given
            if low<=cap<=high:
                results.append((cap,text))
            continue    

        if operator==">" and cap>ref_capacity:
            results.append((cap,text))

        elif operator=="<" and cap<ref_capacity:
            results.append((cap,text))

        elif operator==">=" and cap>=ref_capacity:
            results.append((cap,text))

        elif operator=="<=" and cap<=ref_capacity:
            results.append((cap,text))

        elif operator=="=" and cap==ref_capacity:
            results.append((cap,text))

    #sorted in desc order
    results.sort(reverse=True, key=lambda x:x[0])

    return [text for cap,text in results]


def detect_intent_of_ques(query):
    q=query.lower()
    count_words=["how many","count","number of","total","in total"]
    max_words=["maximum","highest","largest","top","best"]
    min_words=["smallest","minimum","lowest"]

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

def extract_range(query):

    nums=re.findall(r'(\d+)', query.lower())

    if len(nums)>=2:
        low=int(nums[0])
        high=int(nums[1])
        return low,high
    return None