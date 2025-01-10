import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# App configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Import models after db initialization
from models import Story, Comment, Like

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["GET", "POST"])
def submit_story():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        region = request.form.get("region")
        
        if not all([title, content, region]):
            flash("Please fill in all required fields", "error")
            return redirect(request.url)
        
        story = Story(
            title=title,
            content=content,
            region=region,
            submission_date=datetime.datetime.utcnow()
        )
        
        if "media" in request.files:
            file = request.files["media"]
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                story.media_path = filename
        
        db.session.add(story)
        db.session.commit()
        flash("Story submitted successfully!", "success")
        return redirect(url_for("gallery"))
    
    return render_template("submit.html")

@app.route("/gallery")
def gallery():
    region_filter = request.args.get("region")
    if region_filter:
        stories = Story.query.filter_by(region=region_filter).order_by(Story.submission_date.desc()).all()
    else:
        stories = Story.query.order_by(Story.submission_date.desc()).all()
    return render_template("gallery.html", stories=stories)

@app.route("/like/<int:story_id>", methods=["POST"])
def like_story(story_id):
    story = Story.query.get_or_404(story_id)
    like = Like(story_id=story_id)
    db.session.add(like)
    db.session.commit()
    return {"likes": len(story.likes)}

@app.route("/comment/<int:story_id>", methods=["POST"])
def add_comment(story_id):
    story = Story.query.get_or_404(story_id)
    content = request.form.get("content")
    if content:
        comment = Comment(content=content, story_id=story_id)
        db.session.add(comment)
        db.session.commit()
        flash("Comment added successfully!", "success")
    return redirect(url_for("gallery"))

with app.app_context():
    db.create_all()
