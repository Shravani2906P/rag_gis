from rag.res_llm import get_resp

def ai(context,q=""):
    try:
        return get_resp([context],q)
    except:
        return context