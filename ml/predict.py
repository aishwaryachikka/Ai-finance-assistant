"""
Loads the trained expense-classification model and exposes a simple
predict(description) function. Keeps AI/ML logic separate from the Flask
app (SRS non-functional requirement: Maintainability - section 10).
"""
import os
import joblib

HERE = os.path.dirname(__file__)
MODEL_PATH = os.path.join(HERE, "model.pkl")

_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "Model not found. Run `python ml/generate_data.py` then "
                "`python ml/train_model.py` first."
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def predict_category(description: str):
    """Returns (predicted_category, confidence) for a transaction description."""
    bundle = _load()
    pipeline = bundle["pipeline"]
    desc = (description or "").lower().strip()
    if not desc:
        return "Other", 0.0

    proba = pipeline.predict_proba([desc])[0]
    classes = pipeline.classes_
    best_idx = proba.argmax()
    category = classes[best_idx]
    confidence = float(proba[best_idx])
    return category, confidence
