import sqlite3
import random 
from datetime import datetime, timedelta

DB_NAME = "fefo.db"

def generate_batch_id():
    return f"B-{random.randint(10000,99999)}"

demo_batches = {
    ("Tomato",18,12,34.5,"Fresh"),
    ("Leafy Greens",8,24,38.0,"Slightly Wilted")
    ("Banana",25,6,29.0,"Fresh"),
    ("Brinjal",15,18,32.0,"Fresh"),
    ("Mango",20,4,27.5,"Fresh"),
    ("Tamato",10,20,36.5,"Slightly Wilted")
    ("Banana",12,2,25.6,"Fresh"),
    ("Leafy Greens",5,8,35.0,"fresh"),
}    


conn = sqlite3 .connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS batches(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT UNIQUE,
    crop_type TEXT,
    quantity_total INTEGER,
    quantity_sold INTEGER DEFAULT ),
    farm_departure TEXT,
    arrival_time TEXT,
    temp_at_arrival REAL,
    condition TEXT DEFAULT 'Fresh',
    status TEXT DEFAULT 'active,
)
""")

cursor.execute("DELETE FROM batches")
now = datetime.now()
for crop, qty, hours, temp, condition in demo_batches:
    arrival = now- timedelta(hours=hours)
    departure = arival - timedelta(minutes=random.randint(30,120))

    while True:
        batch_id = generate_batch_id()

        try:
            cursor.execute(""" 
            INSERT INTO batches(
                batch_id,
                crop_table,
                quantity_total,
                quantity_sold,
                farm_departure,
                arrival_time,
                temp_at_arrival,
                condition,
                status
            )
            VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                batch_id,
                crop,
                qty,
                0,
                departure.strftime("%Y-%M-%d %H:%M:%S"),
                arrival.strftime("%Y-%M-%d %H:%M:%S"),
                temp,
                condition,
                "active"

            ))
            break
        except sqlite3.IntegrityError:
            continue
conn.commit()
conn.close()

print("8 demo batches inserted successfully.")