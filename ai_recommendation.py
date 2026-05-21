import os
from openai import OpenAI
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "dummy_key"))

def get_recommendations(user_history, catalog):
    if os.getenv("OPENAI_API_KEY") is None:
        return [
            {"title": "Foundation", "reason": "(Placeholder - No API Key) A must-read if you enjoy sci-fi epics."},
            {"title": "Pride and Prejudice", "reason": "(Placeholder - No API Key) Expanding your horizons into classic romance."}
        ]

    prompt = f"""
    You are an expert librarian AI.
    The user has previously read the following books: {user_history}.
    
    Here is the current catalog of available books in our library:
    {catalog}
    
    Based on the user's reading history, recommend up to 2 books from the catalog that they haven't read yet.
    Return a JSON object with a key 'recommendations' containing an array of objects, where each object has a 'title' string and a 'reason' string.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful recommendation assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("recommendations", [])
            
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return [
            {"title": "Service Unavailable", "reason": "Could not fetch AI recommendations at this time."}
        ]
