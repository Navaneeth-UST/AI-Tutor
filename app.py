import os
import re
import uuid
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, render_template

from llm import ask_llm
from validator import (
    validate_input,
    validate_output,
    safe_metadata
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

MAX_HISTORY_MESSAGES = 24


def build_tutoring_prompt(user_message):
    text = (user_message or "").strip()
    if not text:
        return text

    lowered = text.lower()
    concept_match = re.search(
        r"\b(what is|what are|define|explain|tell me about|describe)\b\s+([a-z0-9 _-]{1,40})",
        lowered,
    )

    if concept_match:
        term = concept_match.group(2).strip().strip("?".strip())
        if term:
            return (
                f"{text}\n\nTutor behavior: the learner is asking about the concept '{term}'. "
                "Start by asking what they already think it means. "
                "Do not define it immediately. Keep the response short, conversational, and Socratic."
            )

    return text


@app.route("/")
def index():
    if "history" not in session:
        session["history"] = []
        session["ledger"] = {}
        session["session_id"] = str(uuid.uuid4())

    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "").strip()

    valid, error = validate_input(user_message)

    if not valid:
        return jsonify({"error": error}), 400

    history = session.get("history", [])
    ledger = session.get("ledger", {})

    history.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    history = history[-MAX_HISTORY_MESSAGES:]

    if history and history[-1].get("role") == "user":
        history[-1] = {
            "role": "user",
            "content": build_tutoring_prompt(history[-1].get("content", ""))
        }

    try:
        answer, meta = ask_llm(history)

    except Exception as e:
        return jsonify(
            {
                "error": str(e)
            }
        ), 500

    if meta is None:
        meta = safe_metadata()

    valid, result = validate_output(answer, meta)

    if not valid:
        evaluation = result if isinstance(result, dict) else {}
        return jsonify(
            {
                "reply": result if isinstance(result, str) else "I need a clearer answer to guide you effectively.",
                "phase": meta.get("phase", ""),
                "topic": meta.get("topic", ""),
                "mastery": meta.get("mastery", 0),
                "confidence": evaluation.get("confidence", meta.get("confidence", 0)),
                "precision": evaluation.get("precision", meta.get("precision", 0)),
                "recall": evaluation.get("recall", meta.get("recall", 0)),
                "accuracy": evaluation.get("accuracy", meta.get("accuracy", 0)),
                "ledger": ledger
            }
        )

    confidence = result.get("confidence", 0)

    history.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    session["history"] = history

    topic = meta.get("topic", "").strip()
    # Normalize topic to a consistent workspace key (lowercase, trim, basic
    # singularization) to avoid duplicates like "token" vs "tokens".
    def _normalize_topic(t):
        t = t.strip().lower()
        if not t:
            return t
        # naive singularization: drop trailing 's' for simple plurals
        if t.endswith('s') and not t.endswith('ss'):
            t = t[:-1]
        return t

    norm_topic = _normalize_topic(topic)

    if norm_topic:
        try:
            mastery = int(float(meta.get("mastery", 0)))
        except Exception:
            mastery = 0

        # clamp
        mastery = max(0, min(100, mastery))

        # Smooth updates using exponential moving average so mastery reflects
        # progressive learning instead of noisy single-step jumps.
        previous = int(ledger.get(norm_topic, 0))
        ALPHA = 0.4
        new_mastery = int(round(previous + ALPHA * (mastery - previous)))

        ledger[norm_topic] = max(previous, new_mastery)
        session["ledger"] = ledger

    return jsonify(
        {
            "reply": answer,
            "topic": topic,
            "phase": meta.get("phase", ""),
            "mastery": ledger.get(topic, 0),
            "confidence": confidence,
            "precision": result.get("precision", meta.get("precision", 0)),
            "recall": result.get("recall", meta.get("recall", 0)),
            "accuracy": result.get("accuracy", meta.get("accuracy", 0)),
            "difficulty": meta.get("difficulty", ""),
            "learning_goal": meta.get("learning_goal", ""),
            "next_skill": meta.get("next_skill", ""),
            "ledger": ledger
        }
    )


@app.route("/api/reset", methods=["POST"])
def reset():

    session["history"] = []
    session["ledger"] = {}

    return jsonify(
        {
            "ok": True
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)