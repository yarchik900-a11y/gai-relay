import os
import requests
from flask import Flask, request

app = Flask(__name__)

KEY = os.environ["AQ.Ab8RN6LiBcX4CMP3Yywl7GB5ktH-VurW1nJqi6gcYWV5dZzf5g"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
PROMPT = "You are the G-Man from Half-Life. Speak in his eerie, measured, cryptic way. Reply in 1-2 short sentences, plain text only, no markdown."

@app.route("/ask")
def ask():
    name = request.args.get("name", "someone")[:40]
    q = request.args.get("q", "")[:300]
    try:
        r = requests.post(
            URL,
            headers={"x-goog-api-key": KEY},
            timeout=20,
            json={
                "system_instruction": {"parts": [{"text": PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": name + " says: " + q}]}],
            },
        )
        return r.json()["candidates"][0]["content"]["parts"][0]["text"][:240]
    except Exception:
        return "..."
