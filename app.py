import json, os, sqlite3
from flask import Flask, render_template, request, redirect, jsonify, send_file

app = Flask(__name__)
DB_NAME = "events.json"
SQL_DB = "events.db"

# ---------- JSON Functions ----------
def load_events():
    if not os.path.exists(DB_NAME):
        return {}
    with open(DB_NAME) as f:
        return json.load(f)

def save_events(events):
    tmp_file = DB_NAME + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(events, f, indent=4)
    os.replace(tmp_file, DB_NAME)

# ---------- SQL Setup ----------
def init_sql_db():
    conn = sqlite3.connect(SQL_DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        title TEXT,
        description TEXT,
        date TEXT,
        votes INTEGER
    )
    """)
    conn.commit()
    conn.close()

def update_sql(events):
    """Sync JSON data into SQLite"""
    init_sql_db()
    conn = sqlite3.connect(SQL_DB)
    c = conn.cursor()
    c.execute("DELETE FROM events")  # clear old data
    for k, v in events.items():
        c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                  (int(k), v["title"], v["description"], v["date"], len(v["votes"])))
    conn.commit()
    conn.close()

# ---------- Flask Routes ----------
@app.route("/")
def home():
    events = load_events()
    return render_template("index.html", events=events)

@app.route("/events")
def events():
    events = load_events()
    events_list = [
        {"id": k, "title": v["title"], "start": v["date"],
         "description": v["description"], "votes": len(v["votes"])}
        for k, v in events.items()
    ]
    return jsonify(events_list)

@app.route("/add_event", methods=["POST"])
def add_event():
    events = load_events()
    event_id = str(len(events) + 1)
    events[event_id] = {
        "title": request.form["title"],
        "description": request.form["description"],
        "date": request.form["date"],
        "votes": []
    }
    save_events(events)
    update_sql(events)  # sync SQL
    return redirect("/")

@app.route("/vote/<event_id>", methods=["POST"])
def vote(event_id):
    events = load_events()
    email = request.form["email"]
    if email not in events[event_id]["votes"]:
        events[event_id]["votes"].append(email)
    save_events(events)
    update_sql(events)  # sync SQL
    return redirect("/")

# ---------- Download Routes ----------
@app.route("/download-json")
def download_json():
    return send_file(DB_NAME, as_attachment=True)

@app.route("/download-db")
def download_db():
    return send_file(SQL_DB, as_attachment=True)

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    init_sql_db()
    app.run(host="0.0.0.0", port=port)
