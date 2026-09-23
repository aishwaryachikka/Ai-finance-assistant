"""
Trains the Expense Classification model (SRS section 11.1):
  - TF-IDF to turn transaction descriptions into numeric features
  - Multinomial Naive Bayes classifier (a "suitable beginner algorithm" per SRS 11.1)
  - Evaluated with accuracy, precision, recall, F1 (SRS 11.3)
  - Train/test split kept separate (SRS 11.3)

Run:  python ml/train_model.py
Output: ml/model.pkl  (a dict with the fitted pipeline + label list)
"""
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import joblib

HERE = os.path.dirname(__file__)
DATA_PATH = os.path.join(HERE, "transactions_dataset.csv")
MODEL_PATH = os.path.join(HERE, "model.pkl")


def main():
    if not os.path.exists(DATA_PATH):
        raise SystemExit(
            "Dataset not found. Run `python ml/generate_data.py` first."
        )

    df = pd.read_csv(DATA_PATH)
    X = df["description"]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", MultinomialNB()),
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {acc:.3f}\n")
    print(classification_report(y_test, y_pred))

    joblib.dump({"pipeline": pipeline, "labels": sorted(y.unique().tolist())}, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
