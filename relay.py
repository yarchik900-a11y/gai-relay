import os
import time
import requests
from flask import Flask, request

app = Flask(__name__)

KEY = os.environ["GEMINI_KEY"].strip()
MODELS = [m.strip() for m in os.environ.get("GEMINI_MODELS", "gemini-3.5-flash-lite").split(",") if m.strip()]
PROMPT = "You are G.AI, a friendly and helpful assistant on a Garry's Mod server. Answer clearly in 1-2 short sentences, plain text only, no markdown. Always reply in the same language the player writes in (Russian if they write in Russian, English if they write in English). The player named JluHb is a woman and the owner of this server: always refer to her with feminine forms (in Russian, use feminine grammar) and treat her with respect."
FALLBACK = "The connection is unstable. / Связь нестабильна. Спросите ещё раз."

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
    for model in MODELS:
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
        try:
            r = requests.post(url, headers={"x-goog-api-key": KEY}, json=body, timeout=12)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"][:300]
            print("Gemini error", model, r.status_code, r.text[:150])
        except Exception as e:
            print("Request failed", model, str(e)[:100])
        time.sleep(0.5)
    return FALLBACK
