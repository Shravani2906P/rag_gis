import chainlit as cl
from main import (
    pipeline, format_context_for_llm, get_resp, detect_intent_of_ques,
    extract_entity, extract_operator, get_capacity, extract_range, 
    extract_type, cross_type_compare, capacity_filter
)


@cl.on_chat_start
async def start():
    # Show a loading message while FAISS and the embeddings build
    msg = cl.Message(content="Initializing RAG GIS chatbot... ⏳")
    await msg.send()
    
    # Run your friend's pipeline
    retriever_obj, fuzzy_matcher, kg_retriever, entity_text_map = pipeline()
    
    # Save these objects to the user's session so they persist during the chat
    cl.user_session.set("matcher", fuzzy_matcher)
    cl.user_session.set("kg", kg_retriever)
    cl.user_session.set("map", entity_text_map)

    msg.content = "💧 **Rajasthan Water GIS Chatbot is ready!** Ask your queries."
    await msg.update()

@cl.on_message
async def main(message: cl.Message):
    # Fetch tools from session
    fuzzy_matcher = cl.user_session.get("matcher")
    entity_text_map = cl.user_session.get("map")
    kg_retriever = cl.user_session.get("kg")

    question = message.content
    corrected = fuzzy_matcher.correct(question)

    # Extract info using your friend's functions
    entity = extract_entity(corrected, list(entity_text_map.keys()))
    operator = extract_operator(corrected)
    number = get_capacity(corrected)
    range_vals = extract_range(corrected)
    wbody_types = extract_type(corrected)
    
    type_filter = wbody_types[0] if isinstance(wbody_types, list) and len(wbody_types) == 1 else None

    # --- Step 1: Cross-type comparison ---
    if isinstance(wbody_types, list) and len(wbody_types) == 2 and operator:
        type1, type2 = wbody_types[0], wbody_types[1]
        if "than" in corrected:
            parts = corrected.split("than")
            for t in wbody_types:
                if t in parts[0]: type1 = t
                if t in parts[1]: type2 = t
        
        context = cross_type_compare(type1, type2, operator, entity_text_map)
        if not context:
            await cl.Message(content="No entities satisfy the comparison.").send()
            return
        
        formatted_context = format_context_for_llm(context)
        answer = get_resp(formatted_context, corrected)
        await cl.Message(content=answer).send()
        return

    # --- Step 2: Capacity filtering ---
    if range_vals or operator:
        context = capacity_filter(entity, operator, entity_text_map, range_vals_given=range_vals, number=number)
        if not context:
            await cl.Message(content="No entities match the given criteria :(").send()
            return
            
        formatted_context = format_context_for_llm(context)
        answer = get_resp(formatted_context, corrected)
        await cl.Message(content=answer).send()
        return

    # --- Step 3: KG + FAISS Retrieval ---
    kg_entities = kg_retriever.dynamic_search(corrected)
    context = [entity_text_map[ent] for ent in kg_entities if ent in entity_text_map]

    if type_filter:
        context = [x for x in context if f"is a {type_filter.capitalize()}" in x]

    if not context:
        await cl.Message(content="No relevant data found.").send()
        return

    # --- Step 4: Intent routing (Count, Min, Max) ---
    intent_of_ques = detect_intent_of_ques(corrected)
    formatted_context = format_context_for_llm(context)

    if intent_of_ques == "COUNT":
        count = len(context)
        res = f"There are {count} matching water bodies. Below are the details:\n\n" + "\n".join([f"{i+1}. {it}" for i, it in enumerate(formatted_context)])
        await cl.Message(content=res).send()
        return
        
    if intent_of_ques == "MAX":
        topmax = sorted(context, key=lambda x: int(x.split(" - ")[3].split("M")[0]), reverse=True)[:5]
        answer = get_resp(topmax, corrected)
        await cl.Message(content=answer).send()
        return   
        
    if intent_of_ques == "MIN":
        topmin = sorted(context, key=lambda x: int(x.split(" - ")[3].split("M")[0]), reverse=False)[:5]
        answer = get_resp(topmin, corrected)
        await cl.Message(content=answer).send()
        return   
        
    # --- Default LLM Response ---
    async with cl.Step(name="🔍 View Retrieved GIS Data") as step:
        step.output = "\n".join(formatted_context)
        
    try:
        # We try to get the answer from Gemini
        answer = get_resp(formatted_context, corrected)
        
        # We force it into a string format just in case the Google SDK returns an object
        await cl.Message(content=str(answer)).send()
        
    except Exception as e:
        # 🚨 IF IT FAILS, IT PRINTS THE ERROR HERE INSTEAD OF FREEZING!
        error_message = f"⚠️ **Backend Crash Detected:** Could not generate response.\n\n`{str(e)}`"
        await cl.Message(content=error_message).send()