def confidence(state):

    score=0

    if state.type:score+=1
    if state.area:score+=1
    if state.depth:score+=1
    if state.slope:score+=1

    return score/4


def decide(state):

    conf=confidence(state)

    if state.intent=="chitchat":
        return "CHITCHAT"

    if state.intent=="info":
        return "KG"

    if state.intent=="recommendation":

        if conf<0.25:
            return "EXPLORE"
        if state.area and state.depth:
            return "RECOMMEND"
        if conf<0.5:
            return "REFINE"

        return "RECOMMEND"

    return "FALLBACK"