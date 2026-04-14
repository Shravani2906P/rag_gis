from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import re
import math

from main import (
    pipeline,
    gov_df,
    extract_coordinates,
    detect_type,
    extract_site_features,
    recommend,
    find_nearest_location,
    get_all_types,
    in_range
)
from main import final_df
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
retr,fuzzy,kg,matcher=pipeline()
print("RAG Loaded!")

types_list=get_all_types(gov_df)
types_map={t.lower():t for t in types_list}

aliases={
    "dam":"Pakka Check Dam",
    "anicut":"Anicut",
    "talab":"Talab",
    "pond":"Farm Pond",
    "tank":"Percolation Tank",
    "percolation":"Percolation Tank",
    "johad":"Johad",
    "whs":"WHS",
    "nalah":"Nalah"
}

class Query(BaseModel):
    question:str

def ai(context,q):
    try:
        return get_resp([context],q)
    except:
        return context


def parse_infiltration(val):
    val=str(val)

    if "<" in val:
        num=float(re.findall(r'\d+\.?\d*',val)[0])
        return num-1

    if ">" in val:
        num=float(re.findall(r'\d+\.?\d*',val)[0])
        return num+1

    nums=re.findall(r'\d+\.?\d*',val)
    if nums:
        return float(nums[0])

    return None

def format_rows(rows,title):
    if not rows:
        return "No data available."
    lines=[f"{title}\n"]
    for i,r in enumerate(rows,1):
        area=r.get("area")
        depth=r.get("depth")
        area_text=f"{area} sq meters" if area is not None and not (isinstance(area,float) and math.isnan(area)) else "N/A"
        depth_text=f"{depth} m" if depth is not None and not (isinstance(depth,float) and math.isnan(depth)) else "N/A"
        lines.append(
            f"{i}. {r['type'].title()}\n"
            f"   Village: {r['village']} ({r['panchayat']})\n"
            f"   Location: {r['lat']}, {r['lon']}\n"
            f"   Area: {area_text}\n"
            f"   Depth: {depth_text}"
        )
    return "\n\n".join(lines)

def detect_intent(q):
    q=q.lower()
    if any(w in q for w in ["compare","difference","vs"]):
        return "compare"
    if any(w in q for w in ["highest","maximum","max","lowest","minimum","min"]):
        return "extreme"

    if any(w in q for w in ["slope"]):
        return "slope"
    if any(w in q for w in ["infiltration"]):
        return "feature"
    if any(w in q for w in ["work","id","#"]):
        return "lookup"
    if any(w in q for w in ["district","village","panchayat"]):
        return "location_filter"
    if any(w in q for w in ["list","show","display"]):
        return "list"
    if any(w in q for w in ["count","total","number"]):
        return "count"
    if any(w in q for w in ["top","highest","largest","rank"]):
        return "topk"
    return "other"

@app.post("/ask")
def ask_question(query:Query):

    q=query.question
    corrected=q.lower()

    words=corrected.split()
    
    lat,lon=extract_coordinates(corrected)
    t=detect_type(corrected,types_map,aliases)
    has_numbers=bool(re.search(r'\d',corrected))
    intent=detect_intent(corrected)

    if "infiltration" in corrected and any(w in corrected for w in ["less","more","greater","below","above"]):

        match=re.search(r'\d+\.?\d*',corrected)

        if not match:
            return {"answer":"Provide a numeric value for infiltration."}

        val=float(match.group())

        results=[]

        for _,r in matcher.df.iterrows():

            v=parse_infiltration(r["Infiltration"])

            if v is None:
                continue

            if any(w in corrected for w in ["less","below"]):
                if v < val:
                    results.append(r["Body Type"])

            if any(w in corrected for w in ["more","greater","above"]):
                if v > val:
                    results.append(r["Body Type"])

        if not results:
            return {"answer":"No structures match this condition."}

        return {"answer":"Suitable structures:\n"+"\n".join([f"- {r}" for r in results])}

    if intent=="compare":

        types=[]

        for word in corrected.split():
            detected=detect_type(word,types_map,aliases)
            if detected and detected not in types:
                types.append(detected)

        if len(types)==2:
            rows=matcher.df[matcher.df["Body Type"].isin(types)]

            context=""
            for _,r in rows.iterrows():
                context+=f"""
{r['Body Type']}:
Area: {r['Area']}
Depth: {r['Height / Depth']}
Slope: {r['Slope']}
Infiltration: {r['Infiltration']}
"""
            prompt=f"""
Compare the following two structures clearly:

{context}

Explain differences in simple points:
- Area
- Depth
- Slope
- Infiltration
"""
            return {"answer":ai(prompt,q)}

        else:
            return {"answer":ai("Compare "+q,q)}


    if intent=="extreme":

        if "slope" in corrected:

            best=None

            if any(w in corrected for w in ["lowest","minimum","min"]):
                best_val=999999

                for _,r in matcher.df.iterrows():

                    slope_text=str(r["Slope"])
                    nums=re.findall(r'\d+\.?\d*',slope_text)

                    if nums:
                        val=min([float(n) for n in nums])

                        if val<best_val:
                            best_val=val
                            best=r["Body Type"]

                return {"answer":f"Lowest slope structure: {best}"}

            else:
                max_val=-1

                for _,r in matcher.df.iterrows():

                    slope_text=str(r["Slope"])
                    nums=re.findall(r'\d+\.?\d*',slope_text)

                    if nums:
                        val=max([float(n) for n in nums])

                        if val>max_val:
                            max_val=val
                            best=r["Body Type"]

                return {"answer":f"Highest slope structure: {best}"}

        if "infiltration" in corrected:

            best=None

            if any(w in corrected for w in ["lowest","minimum","min"]):

                best_val=999999

                for _,r in matcher.df.iterrows():

                    val=str(r["Infiltration"])
                    nums=re.findall(r'\d+\.?\d*',val)

                    if nums:
                        v=parse_infiltration(r["Infiltration"])
                        if v is None:
                            continue

                        if v < best_val:
                            best_val=v
                            best=r["Body Type"]

                return {"answer":f"Lowest infiltration structure: {best}"}

            else:

                max_val=-1

                for _,r in matcher.df.iterrows():

                    val=str(r["Infiltration"])
                    nums=re.findall(r'\d+\.?\d*',val)

                    if nums:
                        v=parse_infiltration(r["Infiltration"])
                        if v is None:
                            continue

                        if v > max_val:
                            max_val=v
                            best=r["Body Type"]

                return {"answer":f"Highest infiltration structure: {best}"}

    if intent=="slope":

        match=re.search(r'(\d+)\s*[-–]\s*(\d+)\s*%?',corrected)

        if match:
            q_low,q_high=float(match.group(1)),float(match.group(2))

            results=[]

            for _,r in matcher.df.iterrows():

                slope_text=str(r["Slope"])
                nums=re.findall(r'\d+\.?\d*',slope_text)

                if len(nums)>=2:
                    s_low,s_high=float(nums[0]),float(nums[1])

                    if not (q_high<s_low or q_low>s_high):
                        if t:
                            if t.lower() not in r["Body Type"].lower():
                                continue

                        results.append(r["Body Type"])

            if not results:
                return {"answer":ai("No structures match this slope range.",q)}

            return {"answer":ai("Suitable structures:\n"+"\n".join([f"- {r}" for r in results]),q)}
        if not match:
            return {"answer":ai("Provide slope like 5-15",q)}
        
        

    if intent=="topk":

        match=re.search(r'\d+',corrected)
        k=int(match.group()) if match else 5

        results=[]

        filtered_gov=gov_df.copy()

        if t:
            filtered_gov = filtered_gov[filtered_gov["Work_Name"].str.contains(t, case=False, na=False)]

        for _,r in filtered_gov.iterrows():

            nearest_area=None
            min_d=999999

            for _,f in final_df.iterrows():
                d=(f["avg_lat"]-r["Latitude"])**2+(f["avg_lon"]-r["Longitude"])**2
                if d<min_d:
                    min_d=d
                    nearest_area=f["area_m2"]

            results.append({
            "type":r["Work_Name"],
            "village":r["Village"],
            "panchayat":r["Panchayat"],
            "lat":r["Latitude"],
            "lon":r["Longitude"],
            "area":nearest_area,
            "depth":r["Depth"]
        })

        valid=[r for r in results if r["area"] is not None]

        sorted_rows=sorted(valid,key=lambda x:x["area"],reverse=True)[:k]

        return {"answer":ai(format_rows(sorted_rows,f"Top {k} {t if t else 'Water Bodies'} by Area"),q)}
    
    if has_numbers and not t:

        site=extract_site_features(corrected)
        best=[]

        for _,r in matcher.df.iterrows():
            ok=True

            if "depth" in site:
                if not in_range(site["depth"],str(r["Height / Depth"])):
                    ok=False

            if "area" in site:
                if not in_range(site["area"],str(r["Area"])):
                    ok=False

            if ok:
                best.append(r["Body Type"])

        context="Suitable structures:\n"+("\n".join([f"- {b}" for b in best]) if best else "None")
        return {"answer":ai(context,q)}

    if has_numbers and t:

        site=extract_site_features(corrected)
        result=matcher.check_suitability(site,t)

        if result is None:
            return {"answer":ai(f"No rules found for {t}",q)}
        issues=result.get("issues",[])
        issues_text=", ".join(issues) if issues else "None"
        context=(
            f"Structure: {t}\n"
            f"Depth: {site.get('depth')}\n\n"
            f"Suitable: {result.get('suitable')}\n"
            f"Issues: {issues_text}"
        )
        return {"answer":ai(context,q)}
    
     

    if any(w.startswith("larg") or w.startswith("big") or w.startswith("max") for w in words):

        rows=recommend(gov_df,t if t else "")
        valid=[r for r in rows if r.get("area") is not None and not (isinstance(r.get("area"),float) and math.isnan(r.get("area")))]

        if not valid:
            return {"answer":ai("No valid data found.",q)}

        best=max(valid,key=lambda x:x["area"])
        return {"answer":ai(format_rows([best],"Largest Water Body"),q)}

    if any(w.startswith("small") or w.startswith("min") for w in words):

        rows=recommend(gov_df,t if t else "")
        valid=[r for r in rows if r.get("area") is not None and not (isinstance(r.get("area"),float) and math.isnan(r.get("area")))]

        best=min(valid,key=lambda x:x["area"])
        return {"answer":ai(format_rows([best],"Smallest Water Body"),q)}

    if any(w.startswith("deep") for w in words):

        rows=recommend(gov_df,t if t else "")
        valid=[r for r in rows if r.get("depth") is not None and not (isinstance(r.get("depth"),float) and math.isnan(r.get("depth")))]

        best=max(valid,key=lambda x:x["depth"])
        return {"answer":ai(format_rows([best],"Deepest Water Body"),q)}

    if any(w in corrected for w in ["coordinate","coordinates","lat","lon"]):

        rows=recommend(gov_df,t if t else "")

        lines=[f"Coordinates of {t if t else 'water bodies'}:\n"]

        for r in rows:
            lines.append(f"{r['type']} ({r['village']}) → {r['lat']}, {r['lon']}")

        return {"answer":ai("\n".join(lines),q)}

    if intent=="conditions" and t:

        for _,r in matcher.df.iterrows():
            if r["Body Type"].lower()==t.lower():
                context=(
                    f"Structure: {t}\n"
                    f"Area: {r['Area']}\n"
                    f"Depth: {r['Height / Depth']}\n"
                    f"Slope: {r['Slope']}"
                )
                return {"answer":ai(context,q)}

    if intent=="list":
        rows=recommend(gov_df,t if t else "")
        return {"answer":ai(format_rows(rows,f"{t if t else 'All Water Bodies'}"),q)}

    if intent=="count":
        rows=recommend(gov_df,t if t else "")
        return {"answer":ai(f"Total: {len(rows)}",q)}

    if intent=="location_filter":

        ignore={"list","show","display","in","whs","talab","anicut","tank","percolation"}

        words=[w for w in corrected.split() if w not in ignore]

        rows=[]

        for _,r in gov_df.iterrows():

            text=f"{r['District']} {r['Panchayat']} {r['Village']}".lower()

            if all(w in text for w in words):
                rows.append(r)

        return {"answer":format_rows(rows,"Filtered Results")}
    
    
    

    if intent=="feature":
        best=None
        max_val=0
        for _,r in matcher.df.iterrows():
            val=r["Infiltration"]
            if ">" in str(val):
                num=float(re.findall(r'\d+',val)[0])
                if num>max_val:
                    max_val=num
                    best=r["Body Type"]
        return {"answer":ai(f"Highest infiltration: {best}",q)}

    if intent=="lookup":
        match=re.search(r'\d+',corrected)
        if match:
            wid=int(match.group())
            row=gov_df[gov_df["Sr_no"]==wid]
            if not row.empty:
                r=row.iloc[0]
                return {"answer":ai(
f"""
Work ID: {wid}
Type: {r['Work_Name']}
Village: {r['Village']}
Area: {r['Ar']}
Depth: {r['Depth']}
""",q)}

    if lat and not has_numbers:
        row=find_nearest_location(lat,lon)
        context=(
            f"Nearest structure:\n"
            f"{row['Work_Name']} at {row['Village']}\n"
            f"{row['Latitude']}, {row['Longitude']}"
        )
        return {"answer":ai(context,q)}

    if any(w in corrected for w in ["water bodies","everything","all structures"]):
        rows=recommend(gov_df,"")
        return {"answer":ai(format_rows(rows,"All Water Bodies"),q)}

    return {"answer":"I could not understand the query."}