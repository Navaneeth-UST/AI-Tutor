<<<<<<< HEAD
# Socratic Bench — an AI/Software terminology tutor that teaches by asking first

A Flask app that teaches AI and software engineering terms through **live elicitation**,
not lecturing. Ask about a term (e.g. "what is a token?") and the tutor asks *you* what you
think it means first. Based on your answer, it affirms what's right, corrects what's off,
gives the precise explanation with an example, then checks it stuck with a follow-up — all
rendered as margin annotations next to a running "concept ledger" that tracks mastery per term.

Runs on Groq's free LLM API (Llama 3.3 70B), OpenAI-compatible, fast, no cost for this use case.

## How it works

1. You ask about a term → tutor asks what you already think it means (no answer given yet).
2. You answer → tutor diagnoses your answer: what's right, what's missing/wrong, then the
   correct explanation + example.
3. Tutor asks a follow-up to make you apply the corrected idea.
4. Once solid, you can move to the next term, or ask something new any time.

All of this is driven by a single system prompt in `app.py` (`SYSTEM_PROMPT`) plus a small
JSON metadata block the model appends to every reply (topic, phase, mastery estimate) that
the backend parses to drive the "concept ledger" sidebar. No separate NLP pipeline needed —
the LLM does the diagnosis.

## Project structure
=======
# AI-Tutor
>>>>>>> 53c5101206a9412d867c794deb303ad4e7bf15b2
