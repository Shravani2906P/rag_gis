import re

def extract_features(q):

    nums=re.findall(r'\d+\.?\d*',q)

    features={}

    if "area" in q and nums:
        features["area"]=float(nums[0])

    if "depth" in q and nums:
        features["depth"]=float(nums[-1])

    if "slope" in q:

        if any(w in q for w in ["low","flat","gentle"]):
            features["slope"]=1

        elif any(w in q for w in ["high","steep"]):
            features["slope"]=10

        else:
            nums=re.findall(r'\d+\.?\d*',q)
            if nums:
                features["slope"]=float(nums[0])

    return features