import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
import datetime
from database import db
from services.audio_service import AudioService
from services.image_service import ImageService
from services.storage_service import StorageService
from services.badge_service import BadgeService

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
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
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize services
audio_service = AudioService()
image_service = ImageService()
storage_service = StorageService()
badge_service = BadgeService()

# Import models after db initialization
from models import User, Story, Comment, StoryLike, Tag

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route("/")
def index():
    return render_template("index.html")

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
        tags_input = request.form.get("tags", "")
        generate_audio = request.form.get("generate_audio") == "on"
        generate_image = request.form.get("generate_image") == "on"

        if not all([title, content, region]):
            flash("Please fill in all required fields", "error")
            return redirect(request.url)

        # Create story
        story = Story(
            title=title,
            content=content,
            region=region,
            user_id=current_user.id,
            submission_date=datetime.datetime.utcnow()
        )

        # Handle media upload
        if "media" in request.files:
            file = request.files["media"]
            if file.filename:
                try:
                    file_data = file.read()
                    upload_result = storage_service.upload_media(file_data)
                    if upload_result:
                        story.media_url = upload_result["url"]
                except Exception as e:
                    app.logger.error(f"Error uploading media: {str(e)}")
                    flash("Error uploading media", "error")

        # Generate and store audio narration if requested
        if generate_audio:
            try:
                audio_data = audio_service.generate_audio(content)
                if audio_data:
                    upload_result = storage_service.upload_media(
                        audio_data, 
                        resource_type="audio",
                        public_id=f"audio_{datetime.datetime.utcnow().timestamp()}"
                    )
                    if upload_result:
                        story.audio_url = upload_result["url"]
            except Exception as e:
                app.logger.error(f"Error generating audio: {str(e)}")
                flash("Error generating audio narration", "error")

        # Generate and store AI image if requested
        if generate_image:
            try:
                image_prompt = f"Create an illustration for a story about {title}: {content[:100]}..."
                image_url = image_service.generate_image(image_prompt)
                if image_url:
                    story.generated_image_url = image_url
            except Exception as e:
                app.logger.error(f"Error generating image: {str(e)}")
                flash("Error generating AI image", "error")

        # Process tags
        if tags_input:
            tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                story.tags.append(tag)

        db.session.add(story)
        db.session.commit()

        # After successful story submission, check for new badges
        new_badges = badge_service.check_and_award_badges(current_user)
        if new_badges:
            badge_names = [badge.name for badge in new_badges]
            flash(f"Congratulations! You earned new badges: {', '.join(badge_names)}", "success")

        return redirect(url_for("gallery"))

    return render_template("submit.html")

@app.route("/gallery")
def gallery():
    region_filter = request.args.get("region")
    tag_filter = request.args.get("tag")

    query = Story.query

    if region_filter:
        query = query.filter_by(region=region_filter)

    if tag_filter:
        query = query.join(Story.tags).filter(Tag.name == tag_filter)

    stories = query.order_by(Story.submission_date.desc()).all()
    all_tags = Tag.query.order_by(Tag.name).all()

    return render_template("gallery.html", stories=stories, all_tags=all_tags)

@app.route("/like/<int:story_id>", methods=["POST"])
@login_required
def like_story(story_id):
    story = Story.query.get_or_404(story_id)
    existing_like = StoryLike.query.filter_by(story_id=story_id, user_id=current_user.id).first()

    if existing_like:
        db.session.delete(existing_like)
        action = 'unliked'
    else:
        like = StoryLike(story_id=story_id, user_id=current_user.id)
        db.session.add(like)
        action = 'liked'

    db.session.commit()
    return jsonify({
        'likes': len(story.likes),
        'action': action
    })

@app.route("/comment/<int:story_id>", methods=["POST"])
@login_required
def add_comment(story_id):
    story = Story.query.get_or_404(story_id)
    content = request.form.get("content")
    parent_id = request.form.get("parent_id")

    if content:
        comment = Comment(
            content=content,
            story_id=story_id,
            user_id=current_user.id,
            parent_id=parent_id if parent_id else None
        )
        db.session.add(comment)
        db.session.commit()
        flash("Comment added successfully!", "success")

    return redirect(url_for("gallery"))

@app.route("/profile")
@login_required
def profile():
    user_badges = badge_service.get_user_badges(current_user)
    user_stories = Story.query.filter_by(user_id=current_user.id).order_by(Story.submission_date.desc()).all()
    return render_template("profile.html", badges=user_badges, stories=user_stories)

with app.app_context():
    db.create_all()
    badge_service.initialize_default_badges()