"""
Author: Sahil Gour (@SirSevrus)
"""

import os
import time
import re
import pandas as pd
from flask import Flask, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler

# Import our Java regression wrapper
from libs.lrj import JavaLinearRegression

# ----------------------------
# Data preparation
# ----------------------------
def create_dataframe():
    df = pd.read_csv(
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vTq08vBQuHiahx195CsqRy_kCyRwAQ6eqSa9L1kaZn5gXpSlNAOgGAGnIVe2z4HP8Uu2djZIcADEroC/pub?gid=1413079117&single=true&output=csv"
    )
    df = df[
        [
            "How many hours did you study per day (on average)? ",
            "Your exam percentage (out of 100)?",
        ]
    ].copy()
    df.columns = ["Hours", "Score"]

    def clean_hours(val):
        if pd.isna(val):
            return None
        val = str(val).lower().strip()
        numbers = re.findall(r"[\d\.]+", val)
        if not numbers:
            return None
        numbers = [float(num) for num in numbers]
        if len(numbers) == 1:
            return numbers[0]
        return sum(numbers) / len(numbers)

    def clean_score(val):
        if pd.isna(val):
            return None
        val = str(val).strip().replace("%", "")
        try:
            return float(val)
        except:
            return None

    df["Hours"] = df["Hours"].apply(clean_hours)
    df["Score"] = df["Score"].apply(clean_score)
    df = df.dropna(subset=["Hours", "Score"]).reset_index(drop=True)
    return df


# ----------------------------
# Training
# ----------------------------
def train_model():
    global model
    df = create_dataframe()
    X = df[["Hours"]]
    y = df[["Score"]]

    # Recreate the JavaLinearRegression each time we retrain
    if model is not None:
        model.close()
    t1 = time.time()
    model = JavaLinearRegression()
    model.fit(X, y)
    t2 = time.time()
    print(f"[MODEL] Model trained in {t2 - t1:.2f} seconds")


# ----------------------------
# Flask app
# ----------------------------
app = Flask(__name__)

# Global model
model = None


@app.route("/", methods=["GET", "POST"])
def home():
    global model
    prediction = None

    if request.method == "POST":
        if "hours" in request.form:
            hours = float(request.form["hours"])
            prediction = model.predict(hours)
            prediction = max(0, min(100, prediction))  # clamp between 0–100

    return render_template("index.html", prediction=prediction)


if __name__ == "__main__":
    # Initial training
    train_model()

    # Start scheduler for background retraining
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=train_model, trigger="interval", minutes=10)
    scheduler.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
