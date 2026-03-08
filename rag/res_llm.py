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
You are a helpful GIS assistant that explains information about water bodies.

The information below comes from a trusted dataset. Each line has this format:

Name - Type - Capacity - Purpose

Use ONLY the provided context to answer the question.

Guidelines:

1. Explain the result in simple language so that a normal person can understand.
2. If multiple entities match the query, introduce them first and then list them clearly.
3. If only one entity matches, explain why it is the result.
4. Do not invent information that is not in the context.
5. If the question asks for coordinates, extract them from the text and show them clearly.
6. If no entities match the query, respond exactly with:
   "No entities match the given conditions, try asking other ques :("

Context:
{contexts}

Question:
{ques}

Answer in a clear and friendly way.
"""

    response=client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )

    return response.text.strip()