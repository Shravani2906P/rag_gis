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

from rag.res_llm import get_resp  # added

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading RAG pipeline...")
retr, fuzzy, kg, matcher = pipeline()
print("RAG Loaded!")

types_list=get_all_types(gov_df)
types_map={t.lower(): t for t in types_list}

aliases = {
    "dam": "Pakka Check Dam",
    "anicut": "Anicut",
    "talab": "Talab",
    "pond": "Farm Pond",
    "tank": "Percolation Tank",
    "percolation": "Percolation Tank",
    "whs": "WHS",
    "nalah": "Nalah"
}

class Query(BaseModel):
    question: str


#for better contextsd
def ai(context,q):
    try:
        return get_resp([context],q)
    except:
        return context


def format_rows(rows, title):
    if not rows:
        return "No data available."

    lines=[f"{title}\n"]

    for i, r in enumerate(rows, 1):
        area=r.get("area")
        depth=r.get("depth")

        area_text=f"{area} sq meters" if area and not math.isnan(area) else "N/A"
        depth_text=f"{depth} m" if depth and not math.isnan(depth) else "N/A"

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

    if any(w in q for w in ["requirement","requirements","condition","conditions","spec"]):
        return "conditions"

    if any(w in q for w in ["list","show","display"]):
        return "list"

    if any(w in q for w in ["count","total","number"]):
        return "count"

    return "other"


@app.post("/ask")
def ask_question(query: Query):

    q=query.question
    corrected=fuzzy.correct(q.lower())

    words=corrected.split()

    lat, lon=extract_coordinates(corrected)
    t=detect_type(corrected, types_map, aliases)
    has_numbers=bool(re.search(r'\d', corrected))
    intent=detect_intent(corrected)

    if has_numbers and not t:

        site=extract_site_features(corrected)
        best=[]

        for _, r in matcher.df.iterrows():
            ok=True

            if "depth" in site:
                if not in_range(site["depth"], str(r["Height / Depth"])):
                    ok=False

            if "area" in site:
                if not in_range(site["area"], str(r["Area"])):
                    ok=False

            if ok:
                best.append(r["Body Type"])

        context="Suitable structures:\n" + ("\n".join([f"- {b}" for b in best]) if best else "None")
        return {"answer": ai(context,q)}

    if has_numbers and t:

        site=extract_site_features(corrected)
        result=matcher.check_suitability(site, t)

        if result is None:
            return {"answer": ai(f"No rules found for {t}",q)}

        context=(
            f"Structure: {t}\n"
            f"Depth: {site.get('depth')}\n\n"
            f"Suitable: {result.get('suitable')}\n"
            f"Issues: {', '.join(result.get('issues',[]))}"
        )
        return {"answer": ai(context,q)}

    if any(w.startswith("larg") or w.startswith("big") or w.startswith("max") for w in words):

        rows=recommend(gov_df, t if t else "")
        valid=[r for r in rows if str(r.get("area")) != "nan"]

        if not valid:
            return {"answer": ai("No valid data found.",q)}

        best=max(valid, key=lambda x: x["area"])
        return {"answer": ai(format_rows([best], "Largest Water Body"),q)}

    if any(w.startswith("small") or w.startswith("min") for w in words):

        rows=recommend(gov_df, t if t else "")
        valid=[r for r in rows if str(r.get("area")) != "nan"]

        best=min(valid, key=lambda x: x["area"])
        return {"answer": ai(format_rows([best], "Smallest Water Body"),q)}

    if any(w.startswith("deep") for w in words):

        rows=recommend(gov_df, t if t else "")
        valid=[r for r in rows if str(r.get("depth")) != "nan"]

        best=max(valid, key=lambda x: x["depth"])
        return {"answer": ai(format_rows([best], "Deepest Water Body"),q)}

    if any(w in corrected for w in ["coordinate","coordinates","location","locations","lat","lon"]):

        rows=recommend(gov_df, t if t else "")

        lines=[f"Coordinates of {t if t else 'water bodies'}:\n"]

        for r in rows:
            lines.append(f"{r['type']} ({r['village']}) → {r['lat']}, {r['lon']}")

        return {"answer": ai("\n".join(lines),q)}

    if intent == "conditions" and t:

        for _, r in matcher.df.iterrows():
            if r["Body Type"].lower() == t.lower():
                context = (
                    f"Structure: {t}\n"
                    f"Area: {r['Area']}\n"
                    f"Depth: {r['Height / Depth']}\n"
                    f"Slope: {r['Slope']}"
                )
                return {"answer": ai(context,q)}

    if intent == "list":
        rows = recommend(gov_df, t if t else "")
        return {"answer": ai(format_rows(rows, f"{t if t else 'All Water Bodies'}"),q)}

    if intent == "count":
        rows = recommend(gov_df, t if t else "")
        return {"answer": ai(f"Total: {len(rows)}",q)}

    if lat and not has_numbers:
        row=find_nearest_location(lat, lon)

        context=(
            f"Nearest structure:\n"
            f"{row['Work_Name']} at {row['Village']}\n"
            f"{row['Latitude']}, {row['Longitude']}"
        )
        return {"answer": ai(context,q)}

    if any(w in corrected for w in ["water bodies","everything","all structures"]):
        rows=recommend(gov_df, "")
        return {"answer": ai(format_rows(rows, "All Water Bodies"),q)}

    return {"answer": "I could not understand the query."}