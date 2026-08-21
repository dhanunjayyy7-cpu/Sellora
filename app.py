from flask import Flask, request, redirect, url_for, render_template, flash
import sqlite3
import os
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fefo-mandi-2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "fefo.db")


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT UNIQUE,
            crop_type TEXT,
            quantity_total INTEGER,
            quantity_sold INTEGER DEFAULT 0,
            farm_departure TEXT,
            arrival_time TEXT,
            temp_at_arrival REAL,
            condition TEXT DEFAULT 'Fresh',
            status TEXT DEFAULT 'active'
        )
    """)

    db.commit()
    db.close()


def generate_batch_id():
    db = get_db()

    while True:
        batch_id = f"B-{random.randint(10000, 99999)}"

        exists = db.execute(
            "SELECT id FROM batches WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()

        if not exists:
            db.close()
            return batch_id



CROP_DATA = {
    "Tomato": {
        "q10": 2.5,
        "shelf_life": 72
    },
    "Banana": {
        "q10": 2.0,
        "shelf_life": 96
    },
    "Leafy Greens": {
        "q10": 3.0,
        "shelf_life": 24
    },
    "Brinjal": {
        "q10": 2.0,
        "shelf_life": 48
    },
    "Mango": {
        "q10": 2.5,
        "shelf_life": 120
    }
}


CONDITION_PENALTY = {
    "Fresh": 0,
    "Slightly Wilted": 15,
    "Visibly Damaged": 30
}


def calculate_score(batch):
    """
    Calculates the live FEFO urgency score.

    The score starts at 100 and decreases as produce gets older.

    Step 1:
    Calculate how many hours have passed since the produce
    left the farm.

    Step 2:
    Adjust the effective age based on temperature using the
    Q10 formula.

    Q10 means how much faster deterioration happens when
    temperature increases by 10°C.

    Effective Age =
        Elapsed Hours × Q10 ^ ((Temperature - 25) / 10)

    Step 3:
    Compare effective age with the crop's maximum shelf life.

    Score =
        100 - (Effective Age / Shelf Life × 100)

    Step 4:
    Apply a condition penalty.

    Fresh = 0
    Slightly Wilted = -15
    Visibly Damaged = -30

    Finally, keep the score between 0 and 100.
    """

    crop = CROP_DATA.get(batch["crop_type"])

    if not crop:
        return 100

    departure = datetime.fromisoformat(batch["farm_departure"])

    elapsed_hours = max(
        0,
        (datetime.now() - departure).total_seconds() / 3600
    )

    temperature = float(batch["temp_at_arrival"])

    temperature_factor = crop["q10"] ** (
        (temperature - 25) / 10
    )

    effective_age = elapsed_hours * temperature_factor

    score = 100 - (
        effective_age / crop["shelf_life"] * 100
    )

    score -= CONDITION_PENALTY.get(
        batch["condition"],
        0
    )

    return round(max(0, min(100, score)), 1)


def get_priority(score):
    if score <= 30:
        return "SELL IMMEDIATELY", "red"

    if score <= 60:
        return "SELL TODAY", "yellow"

    return "CAN WAIT", "green"



@app.route("/")
def index():
    return redirect(url_for("dashboard"))




@app.route("/dashboard")
def dashboard():
    db = get_db()

    rows = db.execute(
        "SELECT * FROM batches WHERE status = 'active'"
    ).fetchall()

    db.close()

    batches = []

    for batch in rows:
        score = calculate_score(batch)
        priority, color = get_priority(score)

        batch = dict(batch)

        batch["score"] = score
        batch["priority"] = priority
        batch["color"] = color
        batch["remaining"] = (
            batch["quantity_total"] -
            batch["quantity_sold"]
        )

        batches.append(batch)


    batches.sort(key=lambda x: x["score"])

    urgent_count = sum(
        1 for batch in batches
        if batch["color"] == "red"
    )

    today = datetime.now().date()

    today_batches = []

    for batch in batches:
        arrival_date = datetime.fromisoformat(
            batch["arrival_time"]
        ).date()

        if arrival_date == today:
            today_batches.append(batch)

    total_batches = len(today_batches)

    total_crates = sum(
        batch["quantity_total"]
        for batch in today_batches
    )

    total_sold = sum(
        batch["quantity_sold"]
        for batch in today_batches
    )

    total_remaining = sum(
        batch["remaining"]
        for batch in today_batches
    )

    return render_template(
        "dashboard.html",
        batches=batches,
        urgent_count=urgent_count,
        total_batches=total_batches,
        total_crates=total_crates,
        total_sold=total_sold,
        total_remaining=total_remaining
    )


@app.route("/add", methods=["GET", "POST"])
def add_batch():

    if request.method == "GET":
        return render_template("index.html")

    crop = request.form.get(
        "crop_type",
        ""
    ).strip()

    quantity = request.form.get(
        "quantity",
        ""
    ).strip()

    departure = request.form.get(
        "farm_departure",
        ""
    ).strip()

    temperature = request.form.get(
        "temperature",
        ""
    ).strip()

    condition = request.form.get(
        "condition",
        "Fresh"
    ).strip()

    if not crop or not quantity or not departure or not temperature:
        flash("Please fill in all fields.")
        return redirect(url_for("add_batch"))

    if crop not in CROP_DATA:
        flash("Invalid crop type.")
        return redirect(url_for("add_batch"))

    if condition not in CONDITION_PENALTY:
        flash("Invalid condition.")
        return redirect(url_for("add_batch"))

    try:
        quantity = int(quantity)
        temperature = float(temperature)
        departure_time = datetime.fromisoformat(departure)

    except ValueError:
        flash("Please enter valid values.")
        return redirect(url_for("add_batch"))

    if quantity < 1:
        flash("Quantity must be at least 1 crate.")
        return redirect(url_for("add_batch"))

    if departure_time > datetime.now():
        flash("Farm departure cannot be in the future.")
        return redirect(url_for("add_batch"))

    batch_id = generate_batch_id()

    arrival_time = datetime.now().isoformat(
        timespec="seconds"
    )

    db = get_db()

    db.execute("""
        INSERT INTO batches (
            batch_id,
            crop_type,
            quantity_total,
            quantity_sold,
            farm_departure,
            arrival_time,
            temp_at_arrival,
            condition,
            status
        )
        VALUES (?, ?, ?, 0, ?, ?, ?, ?, 'active')
    """, (
        batch_id,
        crop,
        quantity,
        departure,
        arrival_time,
        temperature,
        condition
    ))

    db.commit()
    db.close()

    flash(
        f"Batch {batch_id} added successfully."
    )

    return redirect(url_for("dashboard"))




@app.route("/sell/<int:id>", methods=["POST"])
def sell_batch(id):

    try:
        sell_quantity = int(
            request.form.get("quantity", 0)
        )

    except ValueError:
        flash("Invalid quantity.")
        return redirect(url_for("dashboard"))

    if sell_quantity <= 0:
        flash("Sell quantity must be greater than 0.")
        return redirect(url_for("dashboard"))

    db = get_db()

    batch = db.execute(
        "SELECT * FROM batches WHERE id = ?",
        (id,)
    ).fetchone()

    if not batch:
        db.close()
        flash("Batch not found.")
        return redirect(url_for("dashboard"))

    remaining = (
        batch["quantity_total"] -
        batch["quantity_sold"]
    )

    if sell_quantity > remaining:
        db.close()

        flash(
            f"Only {remaining} crates are remaining."
        )

        return redirect(url_for("dashboard"))

    new_sold = (
        batch["quantity_sold"] +
        sell_quantity
    )

    if new_sold == batch["quantity_total"]:

        db.execute("""
            UPDATE batches
            SET quantity_sold = ?,
                status = 'completed'
            WHERE id = ?
        """, (
            new_sold,
            id
        ))

    else:

        db.execute("""
            UPDATE batches
            SET quantity_sold = ?
            WHERE id = ?
        """, (
            new_sold,
            id
        ))

    db.commit()
    db.close()

    flash(
        f"{sell_quantity} crate(s) sold."
    )

    return redirect(url_for("dashboard"))



@app.route("/delete/<int:id>", methods=["POST"])
def delete_batch(id):

    db = get_db()

    db.execute(
        "DELETE FROM batches WHERE id = ?",
        (id,)
    )

    db.commit()
    db.close()

    flash("Batch deleted.")

    return redirect(url_for("dashboard"))



if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )