from flask import Flask, render_template, request, redirect
import shelve

app = Flask(__name__)
DB_NAME = "events.db"

def get_events():
    with shelve.open(DB_NAME) as db:
        return dict(db)  # returns a dict of all events

@app.route("/")
def home():
    events = get_events()
    return render_template("index.html", events=events)

@app.route("/add_event", methods=["POST"])
def add_event():
    title = request.form["title"]
    description = request.form["description"]
    date = request.form["date"]

    with shelve.open(DB_NAME, writeback=True) as db:
        event_id = str(len(db) + 1)
        db[event_id] = {"title": title, "description": description, "date": date, "votes": []}

    return redirect("/")

@app.route("/vote/<event_id>", methods=["POST"])
def vote(event_id):
    email = request.form["email"]

    with shelve.open(DB_NAME, writeback=True) as db:
        event = db[event_id]
        if email not in event["votes"]:  # prevent duplicate votes
            event["votes"].append(email)
        db[event_id] = event

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
