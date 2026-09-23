# AI Finance Assistant

A working implementation of the AI Finance Assistant described in the SRS
(v1.0): a personal finance tracker with an AI-based expense categorizer,
budgets, dashboards, spending forecasts, and simple financial insights.

Built to run entirely on your laptop — no cloud account, no external
services. Stack: **Flask** (backend + web pages) + **SQLite** (database) +
**scikit-learn** (ML) + plain HTML/CSS/JS (frontend).

## 1. Prerequisites

- Python 3.9+ installed. Check with:
  ```
  python3 --version
  ```
  (On Windows it may just be `python --version`.)

## 2. Setup (do this once)

Open a terminal in this folder (`finance-assistant/`) and run:

```bash
# 1. Create a virtual environment (keeps this project's packages separate)
python3 -m venv venv

# 2. Activate it
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows (Command Prompt)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate training data and train the ML model
python ml/generate_data.py
python ml/train_model.py

# 5. Create the database
python db.py
```

Step 4 will print a test accuracy and a classification report — that's the
model evaluation the SRS asks for (section 11.3). You should see something
like 85-95% accuracy on the synthetic dataset.

## 3. Run the app

```bash
python app.py
```

Then open your browser to: **http://127.0.0.1:5000**

Register an account, then start adding transactions. When you add an
expense without picking a category, the ML model predicts one for you (you
can also click "Predict Category" to preview it before saving).

## 4. What's implemented (mapped to the SRS)

| SRS Section | Feature | Where |
|---|---|---|
| 9.1 | Register / login / logout, hashed passwords | `app.py`, `/register`, `/login` |
| 9.2 | Add / edit / delete / view transactions | `/transactions` routes, Transactions page |
| 9.3 | AI expense categorization (TF-IDF + Naive Bayes) | `ml/train_model.py`, `ml/predict.py`, `/predict-category` |
| 9.4 | Monthly & category budgets, overspend detection | `/budgets` routes, Budgets page |
| 9.5 | Dashboard: income/expense/balance, category & trend charts | `/dashboard`, Dashboard page |
| 9.6 | Spending prediction (avg of last 3 months) | `/insights` |
| 9.7 | AI insights (high spend, month-over-month, budget warnings) | `/insights` |
| 16 | Database schema (users, transactions, budgets, predictions, insights) | `db.py` |
| 20 | REST API matching the spec | `app.py` |
| 21 | Password hashing, session auth, per-user data isolation, input validation | `app.py` |

**Not implemented** (explicitly out of scope per SRS section 5.2, or listed
as "future enhancements" in section 25): real bank integrations, real-time
stock trading, tax filing, OCR receipt scanning, a conversational chatbot,
and cloud deployment. The `/insights` endpoint gives rule-based +
ML-assisted insights rather than a full conversational chatbot module.

## 5. Retraining the model with your own data

If you want better predictions for your own spending habits: open
`ml/transactions_dataset.csv` in a spreadsheet app, add more real (or
realistic) `description,category` rows in the same format, then re-run:

```bash
python ml/train_model.py
```

This overwrites `ml/model.pkl` with the newly trained model — the running
Flask app picks it up next time it's restarted.

## 6. Project structure

```
finance-assistant/
├── app.py                  # Flask app: all routes (pages + JSON API)
├── db.py                   # SQLite schema + connection helper
├── requirements.txt
├── ml/
│   ├── generate_data.py    # builds a synthetic training dataset
│   ├── train_model.py      # trains + evaluates the classifier
│   ├── predict.py          # loads the model, predicts a category
│   ├── transactions_dataset.csv   (generated)
│   └── model.pkl                  (generated)
├── templates/               # HTML pages (Jinja2)
│   ├── base.html, login.html, register.html
│   ├── dashboard.html, transactions.html, budgets.html
├── static/
│   ├── style.css
│   └── app.js
└── instance/
    └── finance.db           (generated SQLite database)
```

## 7. Troubleshooting

- **`ModuleNotFoundError`** → make sure the virtual environment is activated
  (you should see `(venv)` at the start of your terminal prompt) and that
  you ran `pip install -r requirements.txt`.
- **"Model not found" error** → run `python ml/generate_data.py` then
  `python ml/train_model.py` before starting the app.
- **Port already in use** → another program is using port 5000. Change the
  last line of `app.py` to `app.run(debug=True, port=5050)` and open
  `http://127.0.0.1:5050` instead.
- **Database looks empty / broken** → delete `instance/finance.db` and run
  `python db.py` again to recreate it (this erases all data).
