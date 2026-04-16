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

aliases = {
    "dam":          "Pakka Check Dam",
    "check dam":    "Pakka Check Dam",  # multiword alias
    "anicut":       "Anicut",
     "cct": "Continuous Contour Trench (CCT)",
    "deep cct": "Deep Continuous Contour Trench (Deep CCT)",
    "anicuts":      "Anicut",
    "talab":        "Talab",
    "talabs":       "Talab",
    "pond":         "Farm Pond",
    "farm pond":    "Farm Pond",
    "tank":         "Percolation Tank",
    "percolation":  "Percolation Tank",
    "johad":        "Johad",
    "whs":          "WHS",
    "water harvesting": "WHS",
    "nalah":        "Nalah",
    "nala":         "Nalah",
    "khadin":       "Khadin",
    "khadeen":      "Khadin",
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
    
    intent_patterns = {
        "compare":       r'\b(compare|vs|versus|difference|better)\b',
        "extreme":       r'\b(highest|lowest|maximum|minimum|max|min|most|least)\b',
        "slope":         r'\bslope\b',
        "infiltration":  r'\binfiltration\b',
        "lookup":        r'\b(work id|id|sr\.?no|#)\s*\d+',
        "suitability": r'\b(suitable|recommend|suggest|which|possible|can i build|can i make|what structure)\b',
        "location_filter": r'\b(in|near|around|at)\s+[A-Za-z]',
        "count":         r'\b(how many|count|total|number of)\b',
        "list":          r'\b(list|show|display|give me all)\b',
        "topk":          r'\btop\s*\d+\b',
        "feature_info": r'\b(what|requirements|conditions|criteria|specs|specifications|features|needed)\b',
        "coordinates":   r'\b(coordinates?|location|lat|lon)\b',
    }
    
    for intent, pattern in intent_patterns.items():
        if re.search(pattern, q):
            return intent
    
    return "general"

@app.post("/ask")
def ask_question(query:Query):

    q=query.question
    corrected=q.lower()

    words=corrected.split()
    
    lat,lon=extract_coordinates(corrected)
    t=None
    for word in corrected.split():
        detected=detect_type(word,types_map,aliases)
        if detected:
            t=detected
            break
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
                if v<val:
                    results.append(r["Body Type"])

            if any(w in corrected for w in ["more","greater","above"]):
                if v>val:
                    results.append(r["Body Type"])

        if not results:
            return {"answer":"No structures match this condition."}

        return {"answer":"Suitable structures:\n"+"\n".join([f"- {r}" for r in results])}

    if "infiltration" in corrected:

        values=[]

        for _,r in matcher.df.iterrows():
            v=parse_infiltration(r["Infiltration"])
            if v is not None:
                values.append((v, r["Body Type"]))

        if not values:
            return {"answer": "No data available"}

        values.sort() 

        if any(w in corrected for w in ["low","minimum","min"]):
            selected=values[:3]
            label="Low infiltration structures"

        elif any(w in corrected for w in ["high","maximum","max"]):
            selected=values[-3:]
            label="High infiltration structures"

        else:
            return {"answer": "Please specify high or low infiltration"}

        return {
            "answer": label + ":\n" + "\n".join([f"- {x[1]}" for x in selected])
        }
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
The differnce is as follows :

{context}

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

                        if v>max_val:
                            max_val=v
                            best=r["Body Type"]

                return {"answer":f"Highest infiltration structure: {best}"}

    if intent=="slope":

        slope_type=None

        if any(w in corrected for w in ["low","minimum","flat","gentle"]):
            slope_type="low"

        elif any(w in corrected for w in ["high","steep","maximum"]):
            slope_type="high"

        range_match=re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)',corrected)
        single_match=re.search(r'(\d+\.?\d*)\s*%?',corrected)

        results=[]

        for _,r in matcher.df.iterrows():

            slope_text=str(r["Slope"])
            nums=re.findall(r'\d+\.?\d*',slope_text)

            if not nums:
                continue

            vals=[float(n) for n in nums]

        #case1 ie range input
            if range_match:
                q_low,q_high=float(range_match.group(1)),float(range_match.group(2))

                if len(vals)>=2:
                    s_low,s_high=vals[0],vals[1]

                    if not(q_high<s_low or q_low>s_high):
                        results.append(r["Body Type"])

        #case 2 ie single value input
            elif single_match and not slope_type:
                q_val=float(single_match.group(1))

                if len(vals)>=2:
                    s_low,s_high=vals[0],vals[1]
                    if s_low<=q_val<=s_high:
                        results.append(r["Body Type"])
                else:
                    if abs(vals[0]-q_val)<=2:
                        results.append(r["Body Type"])

        #case3 ie semantic
            elif slope_type=="low":
                if min(vals)<=2:
                    results.append(r["Body Type"])

            elif slope_type=="high":
                if max(vals)>=5:
                    results.append(r["Body Type"])

        if results:
            return {"answer":ai("Suitable structures:\n"+"\n".join([f"- {x}" for x in results]),q)}

        return {"answer":ai("No matching structures found.Try low slope,high slope,or a value like 5%.",q)}
        
        

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
    
    if has_numbers and t:

        site=extract_site_features(corrected)
        if not site:
            return {"answer": f"Please provide valid depth/area for {t}"}
        result=matcher.check_suitability(site,t)

        if result is None:
            return {"answer":ai(f"No rules found for {t}",q)}
        issues=result.get("issues",[])
        if issues:
            return {
            "answer": f"No, {t} is not suitable → " + ", ".join(issues)
        }
        else:
            return {
            "answer": f"Yes, {t} is suitable"
        }
    
    if has_numbers:

        site=extract_site_features(corrected)
        if t:
            result=matcher.check_suitability(site,t)
            if result is None:
                return{"answer": f"No rules found for {t}"}
            
            issues=result.get("issues",[])
            if issues:
                return{
                    "answer": f"No, {t} is not suitable → " + ", ".join(issues)
                }
            else :
                return{
                    "answer": f"Yes, {t} is suitable"
                }
            
        else:    
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

    if "deep" in corrected or "depth" in corrected:

        rows=recommend(gov_df,t if t else "")
        valid=[r for r in rows if r.get("depth") is not None and not (isinstance(r.get("depth"),float) and math.isnan(r.get("depth")))]

        best=max(valid,key=lambda x:x["depth"])
        if "deep" in corrected:
            rows = recommend(gov_df, t if t else "")
            valid = [r for r in rows if r.get("depth") is not None]
            if not valid:
                return {"answer": "No depth data available."}

            best=max(valid, key=lambda x: x["depth"])
            return {"answer": format_rows([best], f"Deepest {t if t else 'Water Body'}")}
        
    if intent in ["feature_info","general"] and t:

        for _,r in matcher.df.iterrows():
            if r["Body Type"].lower()==t.lower():

                context=f"""
{t}:

- Area: {r['Area']}
- Depth: {r['Height / Depth']}
- Slope: {r['Slope']}
- Infiltration: {r['Infiltration']}

Description:
A {t} is a water structure used for storage, recharge, or irrigation depending on design.
"""

                return {"answer": ai(context,q)}    

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
    
    
    

    if intent=="feature_info":
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

    # ---------------- KG FALLBACK START ----------------
    kg_results=kg.dynamic_search(t if t else corrected)
    exact_node=re.sub(r'[^a-z0-9\s]', '', corrected).strip()
    if exact_node in kg.nodes:
        kg_results=[exact_node]
    kg_results=kg_results[:5]    
    if kg_results:

        user_site=extract_site_features(corrected)
        responses=[]
        
        context="Based on your query, here are some relevant water structures:\n\n"

        for node in kg_results:
            area=kg.area_map.get(node)
            depth=kg.depth_map.get(node)
            type_=kg.type_map.get(node)

            if not type_:
                continue
            
            context+=f"""
The structure "{node.title()}" is a {type_} with an area of approximately {area} square meters and a depth of about {depth} meters.
"""
            #filtered it by type
            if t and type_ != t.lower():
                continue

            
            if "area" in user_site and area:
                if abs(area/10000 - user_site["area"]) > 2:
                    continue

            if "depth" in user_site and depth:
                if abs(depth - user_site["depth"]) > 1:
                    continue

            responses.append(
                f"{node} ({type_}) → area: {area} m², depth: {depth} m"
            )

        if responses:
            prompt=f"""
You are an AI assistant.

Explain the following water structure in a natural, human-like way.
Do NOT list points.
Do NOT use headings like "Key results".
Write it as a short paragraph.

Data:
{context}
"""

        return {
            "answer": ai(prompt, q)
        }



    return {"answer":"I could not understand the query."}