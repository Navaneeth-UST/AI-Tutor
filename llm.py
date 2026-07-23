import os
import re
import json
import requests
import urllib3
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

META_RE = re.compile(r"```meta\s*(\{.*?\})\s*```", re.DOTALL)


def build_messages(history):
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        *history
    ]


def split_reply(raw_text):
    meta = {
        "topic": "",
        "phase": "eliciting",
        "mastery": 0,
        "difficulty": "",
        "confidence": 0,
        "precision": 0,
        "recall": 0,
        "accuracy": 0,
        "needs_clarification": False,
        "user_said": "",
        "correction": "",
        "learning_goal": "",
        "next_skill": ""
    }

    visible = raw_text

    match = META_RE.search(raw_text)

    if match:
        visible = raw_text[:match.start()].strip()

        try:
            parsed = json.loads(match.group(1))
            meta.update(parsed)
        except Exception:
            pass

    return visible, meta


def call_groq(messages):
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY not found. Add it to your .env file."
        )

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 700
        },
        timeout=60,
        verify=False
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


def ask_llm(history, retries=2):
    messages = build_messages(history)

    last_error = None

    for _ in range(retries + 1):
        try:
            raw = call_groq(messages)

            answer, meta = split_reply(raw)

            return answer, meta

        except Exception as e:
            last_error = e

    raise RuntimeError(str(last_error))


def debug_response(history):
    answer, meta = ask_llm(history)

    print("\n========== ANSWER ==========\n")
    print(answer)

    print("\n========== META ==========\n")
    print(json.dumps(meta, indent=4))

    return answer, meta