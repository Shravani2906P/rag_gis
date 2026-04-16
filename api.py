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

from decision.intent_model import predict_intent
from decision.state_manager import State
from decision.feature_engine import extract_features
from decision.decision_model import decide
from decision.action_handler import handle
from decision.llm_handler import ai



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

        type_val=r.get("type") or r.get("Work_Name")
        village=r.get("village") or r.get("Village")
        panchayat=r.get("panchayat") or r.get("Panchayat")
        lat=r.get("lat") or r.get("Latitude")
        lon=r.get("lon") or r.get("Longitude")
        area=r.get("area") or r.get("Ar")
        depth=r.get("depth") or r.get("Depth")

        area_text=f"{area}" if area else "N/A"
        depth_text=f"{depth}" if depth else "N/A"

        lines.append(
            f"{i}. {type_val}\n"
            f"   Village: {village} ({panchayat})\n"
            f"   Location: {lat}, {lon}\n"
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

state=State()

@app.post("/ask")
def ask_question(query:Query):

    q=query.question
    corrected=q.lower()

    state.__init__()

    if corrected.strip() in ["hi","hello","hey","hii","heyy","heya","oh","hola"]:
        return {"answer":"Hey! How can I help you today?"}

    has_numbers=bool(re.search(r'\d',corrected))
    intent=detect_intent(corrected)

    intent_ml=predict_intent(corrected)

    if intent_ml in ["chitchat","unknown"] and intent=="general":
        state.__init__()
    
    features=extract_features(corrected)

    
        

    words=corrected.split()
    
    lat,lon=extract_coordinates(corrected)
    t=None
    for word in corrected.split():
        detected=detect_type(word,types_map,aliases)
        if detected:
            t=detected
            break

    state.update(intent=intent_ml,t=t,features=features)

    if lat:

        candidates=[]

        for _,r in gov_df.iterrows():

            if state.depth:
                if r["Depth"] is None or str(r["Depth"])=="nan":
                    continue
                try:
                    if abs(float(r["Depth"])-state.depth)>1:
                        continue
                except:
                    continue

            dist=(r["Latitude"]-lat)**2+(r["Longitude"]-lon)**2

            candidates.append((dist,r))

        if not candidates:
            return {"answer":"No nearby structures match your conditions."}

        candidates.sort(key=lambda x:x[0])
        row=candidates[0][1]

        return {"answer":
        f"Nearest structure:\n"
        f"{row['Work_Name']} at {row['Village']}\n"
        f"{row['Latitude']}, {row['Longitude']}"
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
    
    # for general info like reqments etc
    if intent=="feature_info" and t:

        for _,r in matcher.df.iterrows():
            if r["Body Type"].lower()==t.lower():

                return {"answer":
                f"{t} requirements:\n\n"
                f"• Area: {r['Area']}\n"
                f"• Depth: {r['Height / Depth']}\n"
                f"• Slope: {r['Slope']}\n"
                f"• Infiltration: {r['Infiltration']}"
            }
    #handles depth only queries
    if intent=="suitability" and state.depth and not state.area and not lat:
        return {"answer":"I see you've provided the depth. Could you also share the area of the site so I can give a more accurate recommendation?"}
    #handles area only queries
    if intent=="suitability" and state.area and not state.depth and not lat:
        return {"answer":"I have the area information. Could you also provide the depth so I can suggest suitable structures?"}

#     if intent=="slope":

#         slope_type=None

#         if any(w in corrected for w in ["low","minimum","flat","gentle"]):
#             slope_type="low"

#         elif any(w in corrected for w in ["high","steep","maximum"]):
#             slope_type="high"

#         range_match=re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)',corrected)
#         single_match=re.search(r'(\d+\.?\d*)\s*%?',corrected)

#         results=[]

#         for _,r in matcher.df.iterrows():

#             slope_text=str(r["Slope"])
#             nums=re.findall(r'\d+\.?\d*',slope_text)

#             if not nums:
#                 continue

#             vals=[float(n) for n in nums]

#         #case1 ie range input
#             if range_match:
#                 q_low,q_high=float(range_match.group(1)),float(range_match.group(2))

#                 if len(vals)>=2:
#                     s_low,s_high=vals[0],vals[1]

#                     if not(q_high<s_low or q_low>s_high):
#                         results.append(r["Body Type"])

#         #case 2 ie single value input
#             elif single_match:
#                 q_val=float(single_match.group(1))

#                 if len(vals)>=2:
#                     s_low,s_high=vals[0],vals[1]
#                     if s_low<=q_val<=s_high:
#                         results.append(r["Body Type"])
#                 else:
#                     if abs(vals[0]-q_val)<=2:
#                         results.append(r["Body Type"])

#         #case3 ie semantic
#             elif slope_type=="low":
#                 if min(vals)<=2:
#                     results.append(r["Body Type"])

#             elif slope_type=="high":
#                 if max(vals)>=5:
#                     results.append(r["Body Type"])

#         if results:
#             context="Suitable structures:\n"+"\n".join([f"- {r}" for r in results[:5]])

#             prompt=f"""
# You are an AI assistant.

# Convert the following result into a clean, well-formatted and natural response.

# - Explain briefly why these structures are suitable.
# - Keep it short and readable.
# - Use bullet points.

# Data:
# {context}
# """

#         return {"answer":ai(prompt,q)}

    if intent=="slope" and state.type and state.slope:

        for _,r in matcher.df.iterrows():

            if r["Body Type"].lower()==state.type.lower():

                slope_text=str(r["Slope"])
                nums=re.findall(r'\d+\.?\d*',slope_text)

                if not nums:
                    return {"answer":f"No slope data available for {state.type}."}

                vals=[float(n) for n in nums]

                suitable=False

                if len(vals)>=2:
                    if vals[0]<=state.slope<=vals[1]:
                        suitable=True
                else:
                    if abs(vals[0]-state.slope)<=2:
                        suitable=True

                if suitable:
                    return {"answer":f"Yes,{state.type} is suitable for slope {state.slope}%"}
                else:
                    return {"answer":f"No,{state.type} is not suitable for slope {state.slope}%"}
        
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

            if range_match:
                q_low,q_high=float(range_match.group(1)),float(range_match.group(2))
                if len(vals)>=2:
                    s_low,s_high=vals[0],vals[1]
                    if not(q_high<s_low or q_low>s_high):
                        results.append(r["Body Type"])

            elif single_match:
                q_val=float(single_match.group(1))
                if len(vals)>=2:
                    s_low,s_high=vals[0],vals[1]
                    if s_low<=q_val<=s_high:
                        results.append(r["Body Type"])
                else:
                    if abs(vals[0]-q_val)<=2:
                        results.append(r["Body Type"])

            elif slope_type=="low":
                if min(vals)<=2:
                    results.append(r["Body Type"])

            elif slope_type=="high":
                if max(vals)>=5:
                    results.append(r["Body Type"])

   
        if results:
            results=list(dict.fromkeys(results))

            return {
    "answer":"Suitable structures for this slope:\n\n"+
             "\n".join([f"• {r}" for r in results[:5]])
}

        return {"answer":"No suitable structures found for this slope.Try values like 2%,5%,or ranges."}

    if intent=="slope" and not results:
        return {
        "answer":"I couldn’t match exact slope conditions. Try values like 2%, 5%, or ranges like 2-8%."
    }
    # if "suggest" in corrected or "waterbodies" in corrected or "structures" in corrected:

    #     results=list(dict.fromkeys(matcher.df["Body Type"].tolist()))

    #     return {
    #     "answer":"Here are some commonly suitable water structures:\n\n"+
    #              "\n".join([f"• {r}" for r in results[:7]])
    # }    
    
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
    
    site={"area":state.area,"depth":state.depth}

    if state.type and (state.area or state.depth):
        result=matcher.check_suitability(site,state.type)

        if result and not result.get("issues"):
                return {"answer":f"Yes,{state.type} is suitable"}
        else:
               return {"answer":f"No,{state.type} is not suitable"}

    #if no typ entered, then suggest
    results=[]

    for _,r in matcher.df.iterrows():

        ok=True

        if state.area and not in_range(state.area,str(r["Area"])):
            ok=False

        if state.depth and not in_range(state.depth,str(r["Height / Depth"])):
            ok=False

        if ok:
            results.append(r["Body Type"])

    if results and (state.area or state.depth):

        return {
        "answer":"Suitable structures:\n\n"+
                 "\n".join([f"• {r}" for r in results[:5]])
    }

    
    

    
    


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

        return {"answer":(format_rows(sorted_rows,f"Top {k} {t if t else 'Water Bodies'} by Area"))}
    
    if has_numbers and t:

        site=extract_site_features(corrected)
        if not site:
            return {"answer": f"Please provide valid depth/area for {t}"}
        result=matcher.check_suitability(site,t)

        if result is None:
            return {"answer":(f"No rules found for {t}")}
        issues=result.get("issues")
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
            
            prompt=f"Explain clearly why these structures are suitable:\n{context}"
        
            return {"answer":ai(prompt,q)}

    
    
     

    if any(w.startswith("larg") or w.startswith("big") or w.startswith("max") for w in words):

        rows=recommend(gov_df,t if t else "")
        valid=[r for r in rows if r.get("area") is not None and not (isinstance(r.get("area"),float) and math.isnan(r.get("area")))]

        if not valid:
            return {"answer":ai("No valid data found.",q)}

        best=max(valid,key=lambda x:x["area"])
        return {"answer":(format_rows([best],"Largest Water Body"))}

    if any(w.startswith("small") or w.startswith("min") for w in words):

        rows=recommend(gov_df,t if t else "")
        valid=[r for r in rows if r.get("area") is not None and not (isinstance(r.get("area"),float) and math.isnan(r.get("area")))]

        best=min(valid,key=lambda x:x["area"])
        return {"answer":(format_rows([best],"Smallest Water Body"))}

    # if "deep" in corrected or "depth" in corrected:

    #     rows=recommend(gov_df,t if t else "")
    #     valid=[r for r in rows if r.get("depth") is not None and not (isinstance(r.get("depth"),float) and math.isnan(r.get("depth")))]

    #     best=max(valid,key=lambda x:x["depth"])
    #     if "deep" in corrected:
    #         rows = recommend(gov_df, t if t else "")
    #         valid = [r for r in rows if r.get("depth") is not None]
    #         if not valid:
    #             return {"answer": "No depth data available."}

    #         best=max(valid, key=lambda x: x["depth"])
    #         return {"answer": format_rows([best], f"Deepest {t if t else 'Water Body'}")}
        
    

    if any(w in corrected for w in ["coordinate","coordinates","lat","lon"]):

        rows=recommend(gov_df,t if t else "")

        lines=[f"Coordinates of {t if t else 'water bodies'}:\n"]

        for r in rows:
            lines.append(f"{r['type']} ({r['village']}) → {r['lat']}, {r['lon']}")

        return {"answer":("\n".join(lines))}

    if intent=="conditions" and t:

        for _,r in matcher.df.iterrows():
            if r["Body Type"].lower()==t.lower():
                context=(
                    f"Structure: {t}\n"
                    f"Area: {r['Area']}\n"
                    f"Depth: {r['Height / Depth']}\n"
                    f"Slope: {r['Slope']}"
                )
                return {"answer":(context)}

    if intent=="list":
        rows=recommend(gov_df,t if t else "")
        return {"answer":(format_rows(rows,f"{t if t else 'All Water Bodies'}"))}

    if intent=="count":
        rows=recommend(gov_df,t if t else "")
        return {"answer":(f"Total: {len(rows)}")}

    if intent=="location_filter":

        location_word=None

        for w in corrected.split():
            if w not in ["water","bodies","in","near","around","at","structures","show","list"]:
                if len(w)>2:   
                    location_word=w

        rows=[]

        

        for _,r in gov_df.iterrows():

            text=f"{r['District']} {r['Panchayat']} {r['Village']}".lower()

            if location_word and location_word in text:
                rows.append({
    "type":r["Work_Name"],
    "village":r["Village"],
    "panchayat":r["Panchayat"],
    "lat":r["Latitude"],
    "lon":r["Longitude"],
    "area":r.get("Ar"),
    "depth":r.get("Depth")
})

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
        return {"answer":(f"Highest infiltration: {best}")}

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

    



    

    if any(w in corrected for w in ["water bodies","everything","all structures"]):
        rows=recommend(gov_df,"")
        return {"answer":(format_rows(rows,"All Water Bodies"))}


    if state.area and state.depth:
        action="RECOMMEND"
    else:
        action=decide(state)

    if action!="RECOMMEND":
        response=handle(action,state,kg,matcher,ai,corrected)
        if response and isinstance(response,str) and len(response)<200:
            return {"answer":response}

    #kg retrieval fallback
    kg_results=kg.dynamic_search(t if t else corrected)
    kg_results=kg_results[:5]

    if kg_results and intent!="general":

        user_site=extract_site_features(corrected)

        responses=[]

        for node in kg_results:
            area=kg.area_map.get(node)
            depth=kg.depth_map.get(node)
            type_=kg.type_map.get(node)

            if not type_:
                continue

            responses.append(
            f"{node} ({type_}) → area: {area} m², depth: {depth} m"
            )

        if responses:
            return {
            "answer":"Relevant structures:\n\n"+ "\n".join(responses)
        }



    return {
    "answer":"I couldn’t understand this query.\n\nTry asking:\n"
             "• water bodies in a location\n"
             "• slope-based structures\n"
             "• area and depth conditions\n"
             "• compare structures"
}