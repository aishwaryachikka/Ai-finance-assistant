"""
Generates a synthetic dataset of (description -> category) examples for the
Expense Classification ML use case described in the SRS (section 11.1).

This is a beginner-friendly, fully offline way to get training data without
needing real banking data (the SRS explicitly says real banking data should
not be used without authorization - section 14).

Run:  python ml/generate_data.py
Output: ml/transactions_dataset.csv
"""
import csv
import random
import os

random.seed(42)

# category -> (merchants/keywords, verbs/phrases) used to build realistic-ish descriptions
CATEGORY_TEMPLATES = {
    "Food": {
        "merchants": ["Swiggy", "Zomato", "Dominos", "McDonalds", "Starbucks",
                      "KFC", "Subway", "local cafe", "Pizza Hut", "canteen",
                      "street food", "grocery store", "bakery", "Burger King"],
        "verbs": ["dinner", "lunch", "breakfast", "order", "snacks", "groceries",
                  "coffee", "food delivery", "takeout", "meal"],
    },
    "Transport": {
        "merchants": ["Uber", "Ola", "Rapido", "metro", "bus pass", "petrol pump",
                      "railway", "airport taxi", "parking", "toll"],
        "verbs": ["ride", "fare", "fuel", "recharge", "ticket", "cab", "commute", "top-up"],
    },
    "Shopping": {
        "merchants": ["Amazon", "Flipkart", "Myntra", "H&M", "Zara", "mall",
                      "Nike store", "IKEA", "Decathlon", "local market"],
        "verbs": ["order", "purchase", "clothes", "shoes", "electronics", "furniture", "gadget"],
    },
    "Bills": {
        "merchants": ["electricity board", "water department", "gas agency",
                      "broadband provider", "mobile network", "landlord", "DTH"],
        "verbs": ["bill payment", "recharge", "rent", "monthly bill", "invoice", "subscription fee"],
    },
    "Entertainment": {
        "merchants": ["Netflix", "Spotify", "PVR Cinemas", "BookMyShow", "gaming store",
                      "amusement park", "concert", "YouTube Premium", "Disney+ Hotstar"],
        "verbs": ["subscription", "movie ticket", "streaming", "concert ticket", "game purchase", "outing"],
    },
    "Health": {
        "merchants": ["Apollo Pharmacy", "hospital", "clinic", "dentist", "gym",
                      "diagnostic lab", "physiotherapist", "optician"],
        "verbs": ["consultation", "medicine", "checkup", "membership fee", "treatment", "insurance premium"],
    },
    "Education": {
        "merchants": ["Coursera", "Udemy", "college", "school", "bookstore",
                      "tuition center", "library", "exam board"],
        "verbs": ["course fee", "tuition fee", "book purchase", "exam fee", "certification", "workshop"],
    },
    "Other": {
        "merchants": ["ATM", "bank", "charity", "gift shop", "miscellaneous vendor",
                      "friend", "unknown merchant"],
        "verbs": ["withdrawal", "transfer", "donation", "gift", "miscellaneous expense", "cash payment"],
    },
}

PATTERNS = [
    "{merchant} {verb} {amount}",
    "{verb} at {merchant} {amount}",
    "{merchant} - {verb}",
    "paid {merchant} for {verb} {amount}",
    "{verb} {amount} {merchant}",
    "{merchant} {amount}",
]


def build_rows(n_per_category=60):
    rows = []
    for category, parts in CATEGORY_TEMPLATES.items():
        for _ in range(n_per_category):
            merchant = random.choice(parts["merchants"])
            verb = random.choice(parts["verbs"])
            amount = random.choice([50, 99, 120, 150, 200, 250, 300, 450, 500,
                                     650, 800, 999, 1200, 1500, 2000, 2500])
            pattern = random.choice(PATTERNS)
            desc = pattern.format(merchant=merchant, verb=verb, amount=amount)
            rows.append({"description": desc.lower(), "category": category})
    random.shuffle(rows)
    return rows


def main():
    rows = build_rows()
    out_path = os.path.join(os.path.dirname(__file__), "transactions_dataset.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["description", "category"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
