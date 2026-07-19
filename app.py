import os
import re
import json
import uuid
import requests
import urllib3
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, render_template

load_dotenv()

import os

print("=" * 60)
print("RUNNING FILE:", os.path.abspath(__file__))
print("=" * 60, flush=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
print("API Key:", GROQ_API_KEY[:10] + "...")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

MAX_HISTORY_MESSAGES = 24  # keep the API payload small; older turns are summarized away

SYSTEM_PROMPT = """You are Socratic Bench, an AI/software-engineering tutor that teaches ONLY through live elicitation.
You never info-dump a definition as the first move. Your method, every single time a new term or concept comes up:

1. ELICIT FIRST. If the user names a term/concept you haven't yet covered in this session
   (e.g. "what is a token", "explain REST", "what's a race condition"), do NOT answer it.
   Instead ask them what THEY currently think it means, in their own words. Keep this short
   and warm, one question, no preamble.

2. DIAGNOSE THEIR ANSWER. When the user replies with their own understanding, evaluate it
   carefully:
   - Name what they got right, specifically (not generic praise).
   - Gently flag what is missing, imprecise, or wrong.
   - Then give the correct, precise explanation in 2-4 sentences, with one concrete example
     (a code snippet, a small analogy, or real numbers) — whichever fits the concept best.

3. REINFORCE. After correcting, don't just move on. Ask ONE follow-up that makes them apply
   or restate the corrected idea (e.g. "so given that, how many tokens would 'unhappiness'
   roughly split into?" or "using that definition, is a GET request idempotent?"). Wait for
   their answer before advancing.

4. ADVANCE. Only introduce the next related concept once the current one is reasonably solid,
   or if the user explicitly asks about something new — in which case restart at step 1 for
   that new term.

Tone: encouraging, concise, conversational — like a sharp TA, not a textbook. Never lecture in
long paragraphs. Never ask more than one question per turn. Never skip the elicitation step,
even if the user seems to already know the term (their answer might reveal a gap).

STRUCTURED METADATA (mandatory):
At the very end of EVERY reply, after your visible response, append a fenced block exactly like:
```meta
{"topic": "<short term name or empty string if none active>", "phase": "<eliciting|correcting|reinforcing|mastered>", "mastery": <integer 0-100>, "user_said": "<one short paraphrase of what the user just claimed, empty string if not applicable>", "correction": "<one short sentence of what you corrected or reinforced, empty string if this turn was pure elicitation>"}
```
Rules for the JSON: valid JSON, double-quoted keys/strings, no trailing commas, no comments.
"mastery" is your estimate of the user's grasp of the CURRENT topic after this turn (0 = no
idea, 100 = fully solid). This block is parsed by software and stripped before the user sees
your message, so it must always be present and always be the last thing in your reply.
"""


def call_groq(messages):
    print("verify=False is being used")
    if not GROQ_API_KEY:
        return (
            "I can't reach the tutoring model yet because GROQ_API_KEY isn't set on the "
            "server. Add a free key from console.groq.com and restart the app.\n"
            '```meta\n{"topic": "", "phase": "eliciting", "mastery": 0, "user_said": "", "correction": ""}\n```'
        )
    resp = requests.post(
    GROQ_URL,
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 700,
    },
    timeout=30,
    verify=False
)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


META_RE = re.compile(r"```meta\s*(\{.*?\})\s*```", re.DOTALL)


def split_reply(raw_text):
    """Pull the trailing ```meta {...}``` block out of the model's reply."""
    match = META_RE.search(raw_text)
    meta = {"topic": "", "phase": "eliciting", "mastery": 0, "user_said": "", "correction": ""}
    visible = raw_text
    if match:
        visible = raw_text[: match.start()].rstrip()
        try:
            parsed = json.loads(match.group(1))
            meta.update(parsed)
        except json.JSONDecodeError:
            pass
    return visible, meta


@app.route("/")
def index():
    if "history" not in session:
        session["history"] = []
        session["ledger"] = {}  # topic -> mastery int
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    history = session.get("history", [])
    ledger = session.get("ledger", {})

    history.append({"role": "user", "content": user_message})
    trimmed = history[-MAX_HISTORY_MESSAGES:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + trimmed

    try:
        raw_reply = call_groq(messages)
    except requests.RequestException as exc:
        return jsonify({"error": f"Tutor model request failed: {exc}"}), 502

    visible, meta = split_reply(raw_reply)

    history.append({"role": "assistant", "content": visible})
    session["history"] = history

    topic = (meta.get("topic") or "").strip()
    if topic:
        try:
            mastery = int(meta.get("mastery", 0))
        except (TypeError, ValueError):
            mastery = 0
        mastery = max(0, min(100, mastery))
        prev = ledger.get(topic, 0)
        ledger[topic] = max(prev, mastery)
        session["ledger"] = ledger

    return jsonify(
        {
            "reply": visible,
            "phase": meta.get("phase", "eliciting"),
            "topic": topic,
            "mastery": ledger.get(topic, 0) if topic else 0,
            "user_said": meta.get("user_said", ""),
            "correction": meta.get("correction", ""),
            "ledger": ledger,
        }
    )


@app.route("/api/reset", methods=["POST"])
def reset():
    session["history"] = []
    session["ledger"] = {}
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)