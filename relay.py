import os
import time
import requests
from flask import Flask, request

app = Flask(__name__)

KEY = os.environ["GEMINI_KEY"].strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"
PROMPT = "You are the G-Man from Half-Life. Speak in his eerie, measured, cryptic way. Reply in 1-2 short sentences, plain text only, no markdown."
FALLBACK = "The connection... wavers. Ask me again in a moment."

@app.route("/")
def home():
    return "ok"

@app.route("/ask")
def ask():
    name = request.args.get("name", "someone")[:40]
    q = request.args.get("q", "")[:300]
    body = {
        "system_instruction": {"parts": [{"text": PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": name + " says: " + q}]}],
    }
    for attempt in range(3):
        try:
            r = requests.post(URL, headers={"x-goog-api-key": KEY}, json=body, timeout=15)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"][:240]
            print("Gemini error", r.status_code, r.text[:200])
            if r.status_code not in (429, 500, 503):
                break
        except Exception as e:
            print("Request failed:", e)
        time.sleep(1.5)
    return FALLBACK
