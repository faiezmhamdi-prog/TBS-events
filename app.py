import os
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime

app = Flask(__name__)

# Use Render's DATABASE_URL (Postgres) if available, otherwise local sqlite for dev.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///events.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----- Models -----
class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.String(50), nullable=True)  # keep as string for simplicity
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    votes = db.relationship("Vote", backref="event", cascade="all, delete-orphan", lazy="dynamic")

class Vote(db.Model):
    __tablename__ = "votes"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    __table_args__ = (db.UniqueConstraint("event_id", "email", name="uix_event_email"),)

# Create tables at startup (safe for small apps)
with app.app_context():
    db.create_all()

# ----- Helpers -----
def serialize_event(ev: Event):
    return {
        "id": ev.id,
        "title": ev.title,
        "description": ev.description,
        "date": ev.date,
        "votes": ev.votes.count()
    }

# ----- Routes -----
@app.route("/")
def index():
    # The page will fetch /events via JS; we can still pass nothing and let front-end load JSON.
    return render_template("index.html")

@app.route("/events")
def get_events():
    events = Event.query.order_by(Event.created_at.desc()).all()
    return jsonify([serialize_event(e) for e in events])

@app.route("/add_event", methods=["POST"])
def add_event():
    # Accept both form-encoded and JSON
    data = request.get_json(silent=True)
    if data:
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        date = data.get("date", "").strip()
    else:
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    ev = Event(title=title, description=description, date=date)
    db.session.add(ev)
    db.session.commit()

    # If the client expects JSON, return the new event
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(serialize_event(ev)), 201

    return redirect("/")

@app.route("/vote/<int:event_id>", methods=["POST"])
def vote(event_id):
    data = request.get_json(silent=True)
    if data:
        email = data.get("email", "").strip().lower()
    else:
        email = request.form.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    # ensure event exists
    ev = Event.query.get_or_404(event_id)

    # Try to insert vote; UniqueConstraint prevents duplicates
    v = Vote(event_id=event_id, email=email)
    db.session.add(v)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # already voted
        return jsonify({"status": "already_voted", "votes": ev.votes.count()}), 200

    return jsonify({"status": "ok", "votes": ev.votes.count()}), 201

# Simple health endpoint
@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    # For local dev
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
