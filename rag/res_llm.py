import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_resp(context_chunks, ques):
    contexts="\n".join(context_chunks)

    prompt=f"""
You are a GIS water-conservation assistant.

Answer ONLY using the provided context.

Formatting rules:

1. If the question asks to LIST entities:
   Format as:
   Name - Type - Capacity - Purpose

2. If the question asks to COMPARE entities:
   Clearly compare their capacities numerically.
   State which is larger/smaller.

3. If the question asks for TOP / LARGEST / SMALLEST:
   Select correctly based on capacity.
   Format as:
   Name - Type - Capacity

4. Do not add extra explanation.
5. Do not invent data.
6. If no entities match, respond exactly:
   No entities match the given criteria :(

Context:
{contexts}

Question:
{ques}
"""
    response = client.models.generate_content(
        model="gemini-1.5-flash-lite",
        contents=prompt,
    )

    return response.text.strip()