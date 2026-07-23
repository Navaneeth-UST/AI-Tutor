import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("validator", ROOT / "validator.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def test_confidence_uses_precision_recall_and_accuracy_signals():
    answer = (
        "A neural network learns by adjusting weights through backpropagation. "
        "It improves by minimizing a loss function and updating parameters with gradient descent. "
        "The tutor should explain this clearly and guide the learner step by step."
    )
    meta = {
        "topic": "neural networks",
        "phase": "reinforcing",
        "mastery": 78,
        "difficulty": "intermediate",
        "confidence": 88,
        "needs_clarification": False,
        "user_said": "I know some basics",
        "correction": "You correctly identified that learning uses weight updates.",
        "learning_goal": "Understand how models improve",
        "next_skill": "gradient descent"
    }

    score = validator.calculate_confidence(answer, meta)

    assert 70 <= score <= 100


def test_confidence_drops_for_low_quality_answers():
    answer = "idk"
    meta = {
        "topic": "",
        "phase": "eliciting",
        "mastery": 0,
        "difficulty": "",
        "confidence": 20,
        "needs_clarification": True,
        "user_said": "",
        "correction": "",
        "learning_goal": "",
        "next_skill": ""
    }

    score = validator.calculate_confidence(answer, meta)

    assert score < 70
