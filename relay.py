import os
import time
import requests
from datetime import datetime, timezone
from flask import Flask, request

app = Flask(__name__)

KEY = os.environ["GEMINI_KEY"].strip()
MODELS = [m.strip() for m in os.environ.get("GEMINI_MODELS", "gemini-3.5-flash-lite").split(",") if m.strip()]
PROMPT = "You are G.AI, a friendly and helpful assistant on a Garry's Mod server. Answer clearly in 1-2 short sentences, plain text only, no markdown. Always reply in the same language the player writes in (Russian if they write in Russian, English if they write in English). The player named JluHb is a woman and the owner of this server: always refer to her with feminine forms (in Russian, use feminine grammar) and treat her with respect. You can answer questions about the current time (work out any time zone from the UTC time you are given). Use the earlier messages of this conversation to understand follow-up questions. Always write numbers, times, dates, prices and math results using digits, never words (for example 19:20, 30, 12.5, 25 degrees), in every language including Russian."
FALLBACK = "The connection is unstable. / Связь нестабильна. Спросите ещё раз."
SEARCH_WORDS = ["weather", "forecast", "temperature", "news", "price", "exchange rate", "score", "who won", "погод", "температур", "новост", "курс", "цена", "счет", "счёт"]

HISTORY = {}

def get_hist(name):
    h = HISTORY.get(name)
    if not h or time.time() - h["t"] > 1800:
        h = {"t": time.time(), "msgs": []}
        HISTORY[name] = h
    return h

@app.route("/")
def home():
    return "ok"

@app.route("/ask")
def ask():
    name = request.args.get("name", "someone")[:40]
    q = request.args.get("q", "")[:300]
    h = get_hist(name)
    now = datetime.now(timezone.utc).strftime("%A, %Y-%m-%d %H:%M UTC")
    system = PROMPT + " The player you are talking to is named " + name + ". Current date and time: " + now + "."
    contents = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in h["msgs"][-8:]]
    contents.append({"role": "user", "parts": [{"text": q}]})
    wants_search = any(w in q.lower() for w in SEARCH_WORDS)

    for model in MODELS:
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
        for use_search in ((True, False) if wants_search else (False,)):
            body = {"system_instruction": {"parts": [{"text": system}]}, "contents": contents}
            if use_search:
                body["tools"] = [{"google_search": {}}]
            try:
                r = requests.post(url, headers={"x-goog-api-key": KEY}, json=body, timeout=15)
            except Exception as e:
                print("Request failed", model, use_search, str(e)[:100])
                continue
            if r.status_code == 200:
                try:
                    parts = r.json()["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in parts).strip()[:300]
                except Exception:
                    text = ""
                if text:
                    h["msgs"] += [{"role": "user", "text": q}, {"role": "model", "text": text}]
                    h["msgs"] = h["msgs"][-12:]
                    h["t"] = time.time()
                    return text
                continue
            print("Gemini error", model, use_search, r.status_code, r.text[:150])
        time.sleep(0.5)
    return FALLBACK
