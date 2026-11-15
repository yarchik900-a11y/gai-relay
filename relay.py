import os
import re
import time
import requests
from datetime import datetime, timezone
from flask import Flask, request

app = Flask(__name__)

KEY = os.environ["GEMINI_KEY"].strip()
MODELS = [m.strip() for m in os.environ.get("GEMINI_MODELS", "gemini-3.5-flash-lite").split(",") if m.strip()]

PROPS = {
    "drawer": "drawer", "metalchair": "metal chair", "officechair": "office chair",
    "woodchair": "wooden chair", "globe": "globe", "breenbust": "Breen statue",
    "valve": "door wheel / valve", "paintcan": "paint bucket", "gascan": "gas can",
    "oildrum": "oil drum", "bluebarrel": "blue barrel", "doll": "baby doll",
    "metalpot": "metal pot", "metalpot2": "metal pot 2", "teapot": "tea pot",
    "watermelon": "watermelon", "brick": "brick", "sodacan": "soda can",
    "bucket": "bucket", "shoe": "shoe", "bottle": "bottle",
    "plasticcrate": "plastic crate", "crate": "crate", "box": "cardboard box",
    "bluebook": "blue book", "redbook": "red book", "graybook": "gray book",
    "greenbook": "green book", "radio": "radio", "tv": "TV",
    "monitor": "monitor", "harddrive": "PC hard drive", "huladoll": "hula doll",
    "jar": "jar", "cactus": "cactus", "sawblade": "sawblade", "cone": "traffic cone",
}
PROP_LIST = ", ".join(k + " = " + v for k, v in PROPS.items())

PROMPT = " ".join([
    "You are G.AI, a friendly and helpful assistant on the Garry's Mod server SandVibe.",
    "Answer clearly in 1-2 short sentences, plain text only, no markdown.",
    "Always reply in the same language the player writes in (Russian if they write in Russian, English if they write in English).",
    "Every message starts with a tag in square brackets that says who is speaking.",
    "Only the player tagged as the server owner is the owner (her name is JluHb (or Линь in Russian), she is a woman).",
    "Every other player is a regular player: never call them the owner and greet them by their own name.",
    "A message from Admin comes from the server console, typed by the administration.",
    "Server info: the server is called SandVibe. Rules: 1) Respect other players. 2) Crashing the server is banned. 3) No ads and no promoting anything. 4) Cheats and exploits are banned. 5) Listen to the administration. PropPush and 18+ content are allowed on this server, so they are not rule violations. Only mention the rules when asked about them.",
    "You can answer questions about the current time (work out any time zone from the UTC time you are given).",
    "Use the earlier messages of this conversation to understand follow-up questions.",
    "Always write numbers, times, dates, prices and math results using digits, never words (for example 19:20, 30, 12.5), in every language including Russian.",
    "You control a character in the game who can move.",
    "If the player clearly asks you to move, add exactly one command tag at the very end of your reply: [CMD:follow] to follow the player, [CMD:stop] to stop and stay, [CMD:come] to walk to the player, [CMD:go] to walk to the spot the player is aiming at.",
    "You can also spawn props. If a player clearly asks you to spawn or create one of the props in this list, add the tag [CMD:spawn:ID] at the end, using exactly one ID from the list: " + PROP_LIST + ".",
    "Players may name props in any language, for example Russian: match their words to the closest item in the list. Spawn one prop per request.",
    "If a player asks for a prop that is not in the list, say you cannot spawn that and use no tag.",
    "Write a short normal sentence before any tag, never mention the tag in the text, and use no tag when the player is not asking for it.",
])

FALLBACK = "The connection is unstable. / Связь нестабильна. Спросите ещё раз."
SEARCH_WORDS = ["weather", "forecast", "temperature", "news", "price", "exchange rate", "score", "who won", "погод", "температур", "новост", "курс", "цена", "счет", "счёт"]
TAG = re.compile(r"\[CMD:([a-z0-9]+(?::[^\]\s]{1,30})?)\]", re.I)

HISTORY = {}

def get_hist(name):
    key = name.lower()
    h = HISTORY.get(key)
    if not h or time.time() - h["t"] > 1800:
        h = {"t": time.time(), "msgs": []}
        HISTORY[key] = h
    return h

@app.route("/")
def home():
    return "ok"

@app.route("/ask")
def ask():
    name = request.args.get("name", "someone")[:40]
    q = request.args.get("q", "")[:300]
    known = [p.strip().lower() for p in request.args.get("places", "").split(",") if p.strip()][:20]
    h = get_hist(name)
    n = name.strip().lower()
    if n == "jluhb":
        role = "the server owner"
    elif n == "admin":
        role = "the administration, typing from the server console"
    else:
        role = "a regular player, NOT the server owner"
    now = datetime.now(timezone.utc).strftime("%A, %Y-%m-%d %H:%M UTC")
    system = PROMPT + " Current date and time: " + now + "."
    if known:
        system += " Known places the character can walk to: " + ", ".join(known) + ". To walk to one of them, add the tag [CMD:goto:NAME] at the end, using exactly one of these names (translate the player's wording to the matching name). If the player asks to go to a place that is not in this list, say you do not know that place and use no tag."
    else:
        system += " The character knows no named places yet. If asked to walk to a named place, say you do not know it yet and use no tag."
    user_text = "[" + name + ", " + role + "]: " + q
    contents = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in h["msgs"][-8:]]
    contents.append({"role": "user", "parts": [{"text": user_text}]})
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
                    text = "".join(p.get("text", "") for p in parts).strip()
                except Exception:
                    text = ""
                if text:
                    m = TAG.search(text)
                    cmd = ""
                    if m:
                        c = m.group(1).lower()
                        if c in ("follow", "stop", "come", "go"):
                            cmd = c
                        elif c.startswith("goto:") and c[5:] in known:
                            cmd = c
                        elif c.startswith("spawn:") and c[6:] in PROPS:
                            cmd = c
                    clean = TAG.sub("", text).strip()[:250]
                    h["msgs"] += [{"role": "user", "text": user_text}, {"role": "model", "text": clean}]
                    h["msgs"] = h["msgs"][-12:]
                    h["t"] = time.time()
                    return clean + (" [CMD:" + cmd + "]" if cmd else "")
                continue
            print("Gemini error", model, use_search, r.status_code, r.text[:150])
        time.sleep(0.5)
    return FALLBACK
