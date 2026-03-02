import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_resp(context_chunks, ques):
    contexts = "\n".join(context_chunks)

    prompt = f"""
You are a GIS water-conservation assistant.

Answer ONLY using the context below.

If listing water bodies, return them in this format:

Name - Type - Purpose


Do not add extra explanation.
Do not add numbering.
Do not invent data.
If answer is not found, reply exactly: "Data not available, RAG isnt trained for vague ques!!".

Context:
{contexts}

Question:
{ques}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text.strip()
