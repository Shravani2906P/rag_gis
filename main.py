import pandas as pd
import re
import math

from rag.embed import embedder
from rag.vectordb import vectordatabase
from rag.retrieve_info import retriever
from rag.res_llm import get_resp
from rag.extract import build_entity_vocab_from_csv,extract_csv
from rag.typo_matcher import FuzzyMatcher
from rag.kg_loader import load_kgraph
from rag.kg_retriever import KGRetriever
from rag.feature_matcher import FeatureMatcher


#loaddata
gov_df=pd.read_csv("data/govt.csv")
final_df=pd.read_csv("data/FINAL_WATER_BODIES.csv")

# clean text columns
for col in ["Work_Name","Activity","Village","Panchayat"]:
    gov_df[col]=gov_df[col].astype(str).str.strip().str.lower()



def respond(context,q):
    resp=get_resp(context,q)
    print("\nBot:",resp,"\n")


def extract_coordinates(query):
    matches=re.findall(r'\b\d{1,2}\.\d+\b',query)
    if len(matches)>=2:
        return float(matches[0]),float(matches[1])
    return None,None


def get_all_types(df):
    return list(set(str(x).strip() for x in df["Work_Name"] if str(x).strip()!=""))


def detect_type(text,types_map,aliases):
    text=text.lower()
    text=text.replace("anicuts","anicut")
    text=text.replace("talabs","talab")

    for a in aliases:
        if a in text:
            return aliases[a]

    for k in types_map:
        if k in text:
            return types_map[k]

    return None


def extract_site_features(query):
    site={}
    q=query.lower()

    #for area extraction
    area_match = re.search(
    r'(?:area\s*(?:is|=)?\s*)?(\d+\.?\d*)\s*(ha|hectare|hectares|m2|sqm|sq\s*m)',
    q
)

    if area_match:
        val=float(area_match.group(1))
        unit=area_match.group(2)

        if unit in ["ha","hectare","hectares"]:
            site["area"]=val   #keep in hectares

        elif unit in ["m2","sqm","sq m"]:
            site["area"]=val/10000   #convert into hectares

        else:
            site["area"]=val


    #for depth 
    depth_match = re.search(
    r'(?:depth\s*(?:is|=)?\s*)?(\d+\.?\d*)\s*(m|meter|meters)',
    q
)

    if not depth_match:
        depth_match=re.search(r'(\d+\.?\d*)\s*(m|meter|meters)',q)

    if depth_match:
        val=float(depth_match.group(1))
        unit=depth_match.group(2)

        if unit in ["ha","hectare","hectares"]:
            return {"error":"Depth cannot be in hectares"}

        site["depth"]=val


    return site


def find_nearest_location(lat,lon):
    best=None
    min_d=float("inf")

    for _,r in gov_df.iterrows():
        d=math.sqrt((lat-r["Latitude"])**2+(lon-r["Longitude"])**2)
        if d<min_d:
            min_d=d
            best=r

    return best

def in_range(val, rule):

    rule = str(rule)

    nums = re.findall(r'\d+\.?\d*', rule)
    if not nums:
        return True

    nums = [float(n) for n in nums]

    # case: <1–2
    if "<" in rule:
        return val <= max(nums)

    # case: >12.7
    if ">" in rule:
        return val >= min(nums)

    # case: 1–2
    if len(nums) == 2:
        return nums[0] <= val <= nums[1]

    return val == nums[0]


def recommend(df,t):

    results=[]

    t=t.lower().strip() if t else ""

    for _,r in df.iterrows():

        name=r["Work_Name"]
        activity=r["Activity"]
        area=None
        min_d=999999

        for _,f in final_df.iterrows():
            d=(f["avg_lat"]-r["Latitude"])**2+(f["avg_lon"]-r["Longitude"])**2
            if d<min_d:
                min_d=d
                area=f["area_m2"]
        if not t or t in name or t in activity:
            results.append({
                "village":r["Village"],
                "panchayat":r["Panchayat"],
                "lat":r["Latitude"],
                "lon":r["Longitude"],
                "area":area,
                "depth":r["Depth"],
                "type":r["Work_Name"] 
            })

    return results


def build_context(rows,t):

    if not rows:
        return "No data available."

    lines=[f"Water structures of type {t}:"]

    for r in rows:
        line=f"{r['type']} at {r['village']} ({r['panchayat']}) located at {r['lat']},{r['lon']}"

        if r.get("area"):
            line+=f", area {r['area']} sq meters"
        if r.get("depth"):
            line+=f", depth {r['depth']} meters"

        lines.append(line)

    return "\n".join(lines)



def pipeline():

    texts=extract_csv("data/govt.csv")

    emb=embedder()
    embeddings=emb.embedtext(texts)

    db=vectordatabase(len(embeddings[0]))
    db.add(embeddings,texts)

    vocab=build_entity_vocab_from_csv("data/govt.csv")
    fuzzy=FuzzyMatcher(vocab)

    retr=retriever(db,emb,fuzzy)

    triples=load_kgraph("rag/kgraph.json")
    kg=KGRetriever(triples,emb)

    matcher=FeatureMatcher("data/features.csv")

    return retr,fuzzy,kg,matcher


def main():

    print("System Ready\n")

    retr,fuzzy,kg,matcher=pipeline()

    types_list=get_all_types(gov_df)
    types_map={t.lower():t for t in types_list}

    aliases={
        "dam":"Pakka Check Dam",
        "anicut":"Anicut",
        "talab":"Talab",
        "pond":"Farm Pond",
        "tank":"Percolation Tank",
        "percolation":"Percolation Tank",
        "whs":"WHS",
        "nalah":"Nalah"
    }

    last_results=None
    last_type=None

    while True:

        q=input("USER: ")
        if q.lower()=="exit":
            break

        corrected=fuzzy.correct(q.lower())
        print("\nCorrected:",corrected)

        lat,lon=extract_coordinates(corrected)
        t=detect_type(corrected,types_map,aliases)
        has_numbers=bool(re.search(r'\d',corrected))



        if any(w in corrected for w in ["them","those","give all","show all"]):
            if last_results:
                respond([build_context(last_results,last_type)],q)
            else:
                respond(["No previous data available"],q)
            continue


        if any(w in corrected for w in ["water bodies","waterbodies","everything","all structures"]):
            rows=recommend(gov_df,"")
            last_results=rows
            last_type="All Water Bodies"
            respond([build_context(rows,"All Water Bodies")],q)
            continue

        #for large/small, etc
        if any(w in corrected for w in ["largest","biggest","maximum","max"]):

            rows = recommend(gov_df, t if t else "")

            if not rows:
                respond(["No data available."], q)
                continue

    #ignore nan err
            valid=[r for r in rows if str(r.get("area")) != "nan"]

            if not valid:
                respond(["No valid area data found."], q)
                continue

            best=max(valid, key=lambda x: x["area"])

            context=f"""
Largest {t if t else 'water body'}:

Type: {best['type']}
Village: {best['village']} ({best['panchayat']})
Area: {best['area']} sq meters
Depth: {best.get('depth')}
Location: {best['lat']}, {best['lon']}
"""

            respond([context], q)
            continue


        if any(w in corrected for w in ["smallest","minimum","min"]):

            rows=recommend(gov_df, t if t else "")

            valid=[r for r in rows if str(r.get("area")) != "nan"]

            if not valid:
                respond(["No valid area data found."], q)
                continue

            best=min(valid, key=lambda x: x["area"])

            context=f"""
Smallest {t if t else 'water body'}:

Type: {best['type']}
Village: {best['village']} ({best['panchayat']})
Area: {best['area']} sq meters
"""

            respond([context], q)
            continue


        if any(w in corrected for w in ["deepest","maximum depth"]):

            rows=recommend(gov_df, t if t else "")

            valid=[r for r in rows if str(r.get("depth")) != "nan"]

            if not valid:
                respond(["No valid depth data found."], q)
                continue

            best=max(valid, key=lambda x: x["depth"])

            context=f"""
Deepest {t if t else 'water body'}:

Type: {best['type']}
Village: {best['village']} ({best['panchayat']})
Depth: {best['depth']} meters
"""

            respond([context], q)
            continue


#loc based
        if any(w in corrected for w in ["coordinate","coordinates","location","locations","lat","lon"]):

            rows=recommend(gov_df, t if t else "")

            if not rows:
                respond(["No data available."], q)
                continue

            lines=[f"Coordinates of {t if t else 'water bodies'}:\n"]

            for r in rows:
                lines.append(
            f"{r['type']} at {r['village']} ({r['panchayat']}) → {r['lat']}, {r['lon']}"
        )

            context="\n".join(lines)

            respond([context], q)
            continue

        #for all
        if any(w in corrected for w in ["list","show","display"]):

            rows=recommend(gov_df,t if t else "")
            last_results=rows
            last_type=t if t else "All Water Bodies"

            if not rows:
                context=f"""
No matching {last_type} found.

Available types:
{", ".join(types_list)}

Try:
- show all anicuts
- list talabs
- show water bodies
"""
            else:
                context=f"""
Here are the matching results:

{build_context(rows,last_type)}
"""

            respond([context],q)
            continue


        #count
        if any(w in corrected for w in ["how many","count","total","number"]):

            rows=recommend(gov_df,t if t else "")
            last_results=rows
            last_type=t if t else "All Water Bodies"

            respond([f"Total {last_type}: {len(rows)}"],q)
            continue


        # gen reqmenrs
        if t and not has_numbers:

            for _,r in matcher.df.iterrows():
                if r["Body Type"].lower()==t.lower():

                    context=f"""
Structure: {t}

Typical specifications:
- Area: {r['Area']}
- Depth: {r['Height / Depth']}
- Slope: {r['Slope']}
"""

                    respond([context],q)
                    break
            continue       

        #coords based
        if lat and not has_numbers:
            row=find_nearest_location(lat,lon)

            context=f"""
Nearest structure:
Type: {row['Work_Name']}
Village: {row['Village']}
Coordinates: {row['Latitude']},{row['Longitude']}
"""
            respond([context],q)
            continue


        #only numbers
        if has_numbers and not t:

            site=extract_site_features(corrected)

            best=[]

            for _,r in matcher.df.iterrows():
                ok = True

                if "depth" in site:
                    if not in_range(site["depth"], str(r["Height / Depth"])):
                        ok = False

                #area checks
                if "area" in site:
                    if not in_range(site["area"], str(r["Area"])):
                        ok = False
                if ok:
                    best.append(r["Body Type"])

            if best:
                context=f"""
For the given conditions:

- Depth: {site.get('depth')}
- Area: {site.get('area')}

The following structures are suitable:

{chr(10).join(["- "+b for b in best])}
"""
            else:
                context=f"""
For the given conditions:

- Depth: {site.get('depth')}
- Area: {site.get('area')}

No suitable structures found.
"""

            respond([context],q)
            continue


        #suits or not? type query
        if has_numbers and t:

            site=extract_site_features(corrected)

            if "error" in site:
                respond([site["error"]],q)
                continue

            #if ip is partial
            if "area" not in site and "depth" in site:
                context=f"""
Structure: {t}

Only depth provided: {site.get('depth')} m

Depth is within acceptable range.

However, area is required for full suitability analysis.
"""
                respond([context],q)
                continue

            if "depth" not in site and "area" in site:
                context=f"""
Structure: {t}

Only area provided: {site.get('area')} hectares

Area is within acceptable range.

However, depth is required for full suitability analysis.
"""
                respond([context],q)
                continue

            #full checks
            result=matcher.check_suitability(site,t)

            if result is None:
                respond([f"No rules found for {t}"],q)
                continue

            context=f"""
Structure: {t}
Area: {site.get('area')} hectares
Depth: {site.get('depth')}

Suitable: {result.get('suitable')}
Reasons: {', '.join(result.get('reasons',[]))}
Issues: {', '.join(result.get('issues',[]))}
"""
            respond([context],q)
            continue

        #fallbacks
        respond(["I could not understand the query. Try asking about water bodies or structures."],q)



    if __name__=="__main__":
        main()