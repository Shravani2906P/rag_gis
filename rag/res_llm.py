import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_resp(context_chunks,ques):

    contexts="\n".join(context_chunks)

    prompt=f"""
You are a GIS water-body assistant.

The context already contains the correct candidate entities.

Each line follows this format:
Name - Type - Capacity - Purpose

Your job is to format the final answer.

Rules:

1. If the question asks:
   - "which one"
   - "highest"
   - "largest"
   - "maximum"
   - "top"
   
   → Return ONLY the entity with the **highest capacity**.

2. If the question asks:
   - "smallest"
   - "minimum"
   - "lowest"

   → Return ONLY the entity with the **lowest capacity**.

3. If the question asks to **list or show entities**
   → Return ALL entities exactly as provided.

4. Do NOT invent data.
5. Do NOT modify numbers.
6. Only use the provided context.

7. If the context is empty return exactly:
No entities match the given criteria :(

Context:
{contexts}

Question:
{ques}
"""

    response=client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text.strip()