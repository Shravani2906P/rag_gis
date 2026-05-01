import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_resp(context_chunks,ques):

    if not context_chunks:
        return "No matching data found."

    contexts="\n".join(context_chunks)

    prompt=f"""
You are a GIS decision-support assistant.

IMPORTANT:
- If the query asks "where built", interpret it as CONDITIONS (area, depth, slope).
- If the query asks "where located", interpret it as LOCATIONS (villages, coordinates).


STRICT RULES:
- Use ONLY the provided context.
- Do NOT add any external information.
- Do NOT guess or hallucinate missing values.
- If data is missing, ignore it.
- Be concise and clear.

TASK:
- Explain the results based on the user's query.
- Mention the filtering condition (if any).
- Summarize key observations.

DATA FORMAT:
Each entry contains:
Village, Panchayat, Coordinates, Area (m²), Depth (m)

CONTEXT:
{contexts}

USER QUERY:
{ques}

OUTPUT FORMAT:
- 1–2 line explanation
- Then list key results in short form

ANSWER:
"""

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(prompt)

    return response.text.strip()