def handle(action,state,kg,matcher,ai,q):

    if action=="CHITCHAT":
        return ai("Respond naturally to the user greeting or casual message.",q)

    if action=="EXPLORE":
        return ai("Ask what the user wants to build and their goal",q)

    if action=="REFINE":
        if state.area and state.depth:
            return "Proceeding with available data..."
        return ai(
f"""
User wants recommendation.

Known:
type:{state.type}
area:{state.area}
depth:{state.depth}
slope:{state.slope}

Ask ONE specific question to improve accuracy.
""",q)

    if action=="RECOMMEND":

        site={"area":state.area,"depth":state.depth}

        if state.type:
            result=matcher.check_suitability(site,state.type)
            return str(result)

        return ai("Suggest suitable structures based on data",q)

    if action=="KG":
        nodes=kg.dynamic_search(q)
        return str(nodes[:5])

    return "I couldn’t understand this query."