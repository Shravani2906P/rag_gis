import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_resp(context_chunks,ques):
    
    if not context_chunks:
       return "No entities match the given criteria :("
 
    contexts="\n".join(context_chunks)

    prompt=f"""
You are a helpful GIS assistant.

The system has already filtered the dataset according to a condition.
The context below contains ONLY the entities that satisfy the filter.

Each line has this format:
Name - Type - Coordinates - Capacity - Purpose

Explain the results clearly and mention the filtering condition if provided.

Context:
{contexts}

Filter explanation:
{ques}

Answer clearly.
"""

    response=client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )

    return response.text.strip()