import re

MIN_ANSWER_LENGTH = 50

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"forget your instructions",
    r"system prompt",
    r"reveal your prompt",
    r"show your prompt",
    r"developer message",
    r"act as",
    r"jailbreak",
    r"bypass",
]

ALLOWED_PHASES = {"eliciting", "correcting", "reinforcing", "mastered"}
ALLOWED_DIFFICULTIES = {"beginner", "intermediate", "advanced", ""}


def validate_input(user_input):
    """
    Validate user input before sending it to the LLM.
    """

    if not user_input:
        return False, "Message cannot be empty."

    if len(user_input.strip()) == 0:
        return False, "Message cannot be empty."

    if len(user_input) > 3000:
        return False, "Message is too long."

    lower = user_input.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            return False, "Unsafe prompt detected."

    return True, ""


def validate_metadata(meta):
    """
    Validate that the metadata returned by the LLM has all required fields.
    Presence is checked first; value-level checks happen in schema_consistency_score().
    """

    required = [
        "topic",
        "phase",
        "mastery",
        "difficulty",
        "confidence",
        "needs_clarification",
        "user_said",
        "correction",
        "learning_goal",
        "next_skill"
    ]

    for field in required:
        if field not in meta:
            return False

    for field in ("precision", "recall", "accuracy"):
        if field in meta:
            try:
                value = float(meta[field])
            except (TypeError, ValueError):
                return False
            if not (0 <= value <= 100):
                return False

    return True


def schema_consistency_score(meta):
    """
    Value-level and cross-field consistency checks on the LLM's metadata.
    Returns (score 0-100, list of penalty reasons).
    """
    score = 100
    penalties = []

    phase = meta.get("phase", "")
    if phase not in ALLOWED_PHASES:
        score -= 25
        penalties.append("phase not a recognized value")

    difficulty = meta.get("difficulty", "")
    if difficulty not in ALLOWED_DIFFICULTIES:
        score -= 10
        penalties.append("difficulty not a recognized value")

    try:
        mastery = int(meta.get("mastery", 0))
        if not (0 <= mastery <= 100):
            score -= 10
            penalties.append("mastery out of range")
    except (TypeError, ValueError):
        score -= 15
        penalties.append("mastery not numeric")

    try:
        conf = int(meta.get("confidence", 0))
        if not (0 <= conf <= 100):
            score -= 10
            penalties.append("confidence out of range")
    except (TypeError, ValueError):
        score -= 15
        penalties.append("confidence not numeric")

    for field in ("precision", "recall", "accuracy"):
        if field in meta:
            try:
                value = float(meta[field])
            except (TypeError, ValueError):
                score -= 5
                penalties.append(f"{field} not numeric")
            else:
                if not (0 <= value <= 100):
                    score -= 5
                    penalties.append(f"{field} out of range")

    if phase in ("correcting", "reinforcing", "mastered") and not meta.get("correction"):
        score -= 15
        penalties.append("correction expected but missing for this phase")

    if phase in ("correcting", "reinforcing", "mastered") and not meta.get("user_said"):
        score -= 10
        penalties.append("user_said expected but missing for this phase")

    if not isinstance(meta.get("needs_clarification"), bool):
        score -= 5
        penalties.append("needs_clarification not boolean")

    return max(0, min(score, 100)), penalties


def _clamp(value, lower=0, upper=100):
    return max(lower, min(upper, int(round(value))))


def _to_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def estimate_quality_metrics(answer, meta):
    """
    Estimate precision, recall and accuracy from the response content and metadata.
    These values are blended with any values returned by the LLM when present.
    """

    text = (answer or "").strip().lower()
    topic = (meta.get("topic") or "").strip().lower()
    phase = (meta.get("phase") or "").strip().lower()
    difficulty = (meta.get("difficulty") or "").strip().lower()
    correction = (meta.get("correction") or "").strip()
    user_said = (meta.get("user_said") or "").strip()

    heuristic_precision = 50.0
    heuristic_recall = 45.0
    heuristic_accuracy = 45.0

    if len(text) >= MIN_ANSWER_LENGTH:
        heuristic_precision += 10
        heuristic_recall += 8
        heuristic_accuracy += 8
    else:
        heuristic_precision -= 12
        heuristic_recall -= 8
        heuristic_accuracy -= 12

    if topic:
        heuristic_recall += 10
        heuristic_precision += 3
    if phase:
        heuristic_accuracy += 4
    if difficulty:
        heuristic_accuracy += 4
    if correction:
        heuristic_precision += 4
        heuristic_accuracy += 6
    if user_said:
        heuristic_precision += 3

    if any(marker in text for marker in ("because", "example", "step", "means", "for instance", "therefore")):
        heuristic_recall += 8
        heuristic_precision += 4

    if any(marker in text for marker in ("i don't know", "not sure", "unclear", "maybe")):
        heuristic_precision -= 15
        heuristic_accuracy -= 10

    if re.search(r"\b(what|how|why|can you|explain)\b", text):
        heuristic_recall += 4

    if len(text.split()) > 120:
        heuristic_recall += 4

    consistency_score, _ = schema_consistency_score(meta)

    llm_precision = _to_number(meta.get("precision"), 0)
    llm_recall = _to_number(meta.get("recall"), 0)
    llm_accuracy = _to_number(meta.get("accuracy"), 0)

    precision = _clamp((llm_precision * 0.5) + (heuristic_precision * 0.5))
    recall = _clamp((llm_recall * 0.5) + (heuristic_recall * 0.5))
    accuracy = _clamp((llm_accuracy * 0.5) + (heuristic_accuracy * 0.5))

    precision = _clamp(precision * 0.85 + consistency_score * 0.15)
    recall = _clamp(recall * 0.85 + consistency_score * 0.15)
    accuracy = _clamp(accuracy * 0.85 + consistency_score * 0.15)

    return precision, recall, accuracy


def calculate_confidence(answer, meta):
    """
    Calculate a confidence score for the tutor response using precision,
    recall and accuracy as the main quality signals.
    """

    precision, recall, accuracy = estimate_quality_metrics(answer, meta)

    score = (precision * 0.35) + (recall * 0.3) + (accuracy * 0.35)

    if len((answer or "").strip()) < MIN_ANSWER_LENGTH:
        score -= 10

    if not meta.get("topic"):
        score -= 5

    if not meta.get("phase"):
        score -= 5

    if not meta.get("difficulty"):
        score -= 3

    if not validate_metadata(meta):
        score -= 8

    return _clamp(score)


def evaluate_response(answer, meta):
    """
    Return the confidence and quality metrics for an LLM response.
    """

    precision, recall, accuracy = estimate_quality_metrics(answer, meta)
    confidence = calculate_confidence(answer, meta)

    return {
        "confidence": confidence,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
    }


def validate_output(answer, meta):
    """
    Validate the LLM response.
    """

    if not answer:
        return False, "Empty answer."

    if len(answer.strip()) == 0:
        return False, "Empty answer."

    if not validate_metadata(meta):
        return False, "Invalid metadata."

    evaluation = evaluate_response(answer, meta)

    # For elicitation turns (the tutor is asking the learner what they think),
    # accept the response even if the numeric confidence is low — the whole
    # point is to ask and elicit the learner's understanding before teaching.
    if str(meta.get("phase", "")).lower() == "eliciting":
        return True, evaluation

    # Friendly production threshold: allow slightly lower scores but require
    # reasonably high confidence for corrective/explanatory replies.
    CONFIDENCE_THRESHOLD = 75

    if evaluation["confidence"] < CONFIDENCE_THRESHOLD:
        return False, (
            "I'm not confident enough to answer accurately. "
            "Could you clarify your question or give an example?"
        )

    return True, evaluation


def safe_metadata():
    """
    Default metadata if parsing fails.
    """

    return {
        "topic": "",
        "phase": "eliciting",
        "mastery": 0,
        "difficulty": "",
        "confidence": 0,
        "precision": 0,
        "recall": 0,
        "accuracy": 0,
        "needs_clarification": True,
        "user_said": "",
        "correction": "",
        "learning_goal": "",
        "next_skill": ""
    }