import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from database import db
from models import User, Story, Comment, StoryLike, Tag

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__)

# App configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database and create tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route("/")
def index():
    """Home page with featured stories"""
    try:
        # Get featured stories (most liked and commented)
        featured_stories = (
            Story.query
            .outerjoin(StoryLike)
            .group_by(Story.id)
            .order_by(db.func.count(StoryLike.id).desc())
            .limit(6)
            .all()
        )

        # Get recent stories
        recent_stories = (
            Story.query
            .order_by(Story.submission_date.desc())
            .limit(6)
            .all()
        )

        return render_template(
            "index.html",
            featured_stories=featured_stories,
            recent_stories=recent_stories
        )
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash("Error loading stories", "error")
        return render_template("index.html", featured_stories=[], recent_stories=[])

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password", "error")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("index"))

@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit_story():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        region = request.form.get("region")

        if not all([title, content, region]):
            flash("Please fill in all required fields", "error")
            return redirect(request.url)

        try:
            # Create story
            story = Story(
                title=title,
                content=content,
                region=region,
                user_id=current_user.id,
                submission_date=datetime.datetime.utcnow()
            )
            db.session.add(story)
            db.session.commit()

            flash("Story submitted successfully!", "success")
            return redirect(url_for("view_story", story_id=story.id))

        except Exception as e:
            logger.error(f"Error saving story: {str(e)}")
            db.session.rollback()
            flash("Error saving your story", "error")
            return redirect(request.url)

    return render_template("submit.html")

@app.route("/story/<int:story_id>")
def view_story(story_id):
    """View a single story"""
    story = Story.query.get_or_404(story_id)
    return render_template("view_story.html", story=story)

@app.route("/profile")
@login_required
def profile():
    """User profile with their stories"""
    try:
        user_stories = Story.query.filter_by(user_id=current_user.id)\
            .order_by(Story.submission_date.desc()).all()

        return render_template(
            "profile.html",
            stories=user_stories
        )
    except Exception as e:
        logger.error(f"Error in profile route: {str(e)}")
        flash("Error loading profile data", "error")
        return render_template("profile.html", stories=[])