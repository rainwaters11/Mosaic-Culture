import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_caching import Cache
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from database import db
from services.audio_service import AudioService
from services.image_service import ImageService
from services.storage_service import StorageService
from services.badge_service import BadgeService
from services.story_service import StoryService
from services.tag_service import TagService
from services.cultural_context_service import CulturalContextService

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
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Configure caching
app.config["CACHE_TYPE"] = "simple"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300  # 5 minutes default cache timeout
cache = Cache(app)

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
story_service = StoryService()
tag_service = TagService()
cultural_context_service = CulturalContextService()

# Import models after db initialization
from models import User, Story, Comment, StoryLike, Tag, Badge, UserBadge

# Initialize database and create default badges
logger.info("Initializing database and default badges...")
with app.app_context():
    try:
        db.create_all()
        badge_service.initialize_default_badges()
        logger.info("Database and badges initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

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

        try:
            # Create story first to get the ID
            story = Story(
                title=title,
                content=content,
                region=region,
                user_id=current_user.id,
                submission_date=datetime.datetime.utcnow()
            )
            db.session.add(story)
            db.session.flush()  # Get the story ID without committing

            # Handle media upload if provided
            if "media" in request.files:
                file = request.files["media"]
                if file.filename:
                    try:
                        file_data = file.read()
                        upload_result = storage_service.upload_media(file_data)
                        if upload_result:
                            story.media_url = upload_result["url"]
                    except Exception as e:
                        logger.error(f"Error uploading media: {str(e)}")
                        flash("Error uploading media", "error")

            # Generate and store AI image if requested
            if generate_image:
                try:
                    logger.info("Generating AI image for story")
                    image_prompt = f"Create an illustration for '{title}': {content[:200]}..."
                    image_url = image_service.generate_image(image_prompt)
                    if image_url:
                        story.generated_image_url = image_url
                        logger.info(f"Successfully generated image: {image_url}")
                    else:
                        logger.error("Failed to generate image: No URL returned")
                        flash("Could not generate AI image", "warning")
                except Exception as e:
                    logger.error(f"Error generating image: {str(e)}")
                    flash("Error generating AI image", "error")

            # Generate and store audio narration if requested
            if generate_audio:
                try:
                    logger.info("Generating audio narration")
                    audio_data = audio_service.generate_audio(content)
                    if audio_data:
                        upload_result = storage_service.upload_media(
                            audio_data,
                            resource_type="audio",
                            public_id=f"audio_{datetime.datetime.utcnow().timestamp()}"
                        )
                        if upload_result:
                            story.audio_url = upload_result["url"]
                            logger.info(f"Successfully generated audio: {upload_result['url']}")
                        else:
                            logger.error("Failed to upload audio: No URL returned")
                            flash("Could not save audio narration", "warning")
                    else:
                        logger.error("Failed to generate audio: No audio data returned")
                        flash("Could not generate audio narration", "warning")
                except Exception as e:
                    logger.error(f"Error generating audio: {str(e)}")
                    flash("Error generating audio narration", "error")

            # Process tags with cultural suggestions
            if tags_input or content:  # Check both user tags and story content
                try:
                    # Get user-provided tags
                    user_tags = [t.strip().lower() for t in tags_input.split(',') if t.strip()]

                    # Get AI-suggested cultural tags if there's story content
                    suggested_tags = []
                    if content:
                        suggested_tags = tag_service.suggest_cultural_tags(content, region)

                    # Combine user tags and suggested tags (removing duplicates)
                    all_tags = list(set(user_tags + suggested_tags))

                    # Create or get tags and associate with story
                    for tag_name in all_tags:
                        tag = tag_service.create_or_get_tag(tag_name)
                        if tag and tag not in story.tags:
                            story.tags.append(tag)

                    logger.info(f"Processed tags for story {story.id}: {all_tags}")
                except Exception as e:
                    logger.error(f"Error processing tags: {str(e)}")
                    flash("Error processing tags", "error")

            # Commit all changes
            try:
                db.session.commit()
                logger.info(f"Successfully saved story with ID: {story.id}")
                flash("Your story has been submitted successfully!", "success")

                # Check for new badges
                new_badges = badge_service.check_and_award_badges(current_user)
                if new_badges:
                    badge_names = [badge.name for badge in new_badges]
                    flash(f"Congratulations! You earned new badges: {', '.join(badge_names)}", "success")

            except Exception as e:
                logger.error(f"Error saving story: {str(e)}")
                db.session.rollback()
                flash("Error saving your story", "error")
                return redirect(url_for("submit_story"))

            return redirect(url_for("gallery"))

        except Exception as e:
            logger.error(f"Unexpected error in submit_story: {str(e)}")
            flash("An unexpected error occurred", "error")
            return redirect(url_for("submit_story"))

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

@app.route("/generate_story", methods=["POST"])
@login_required
@cache.memoize(timeout=300)  # Cache for 5 minutes
def generate_story():
    """Generate a story with caching to avoid repeated API calls"""
    try:
        data = request.get_json()
        cache_key = f"story_{data.get('title')}_{data.get('theme')}_{data.get('region')}"

        # Try to get from cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info("Returning cached story generation result")
            return jsonify(cached_result)

        title = data.get("title")
        theme = data.get("theme")
        region = data.get("region")

        if not all([title, theme, region]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        generated_content = story_service.generate_story(title, theme, region)
        if generated_content:
            try:
                import json
                sensitivity_analysis = generated_content.get("sensitivity_analysis")
                analysis = json.loads(sensitivity_analysis) if sensitivity_analysis else {}

                result = {
                    "success": True,
                    "content": generated_content["content"],
                    "sensitivity": {
                        "rating": analysis.get("overall_rating", 0),
                        "positive_aspects": analysis.get("positive_aspects", []),
                        "suggestions": analysis.get("improvement_suggestions", ""),
                        "issues": analysis.get("issues", [])
                    }
                }

                # Cache the successful result
                cache.set(cache_key, result)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error parsing sensitivity analysis: {str(e)}")
                result = {
                    "success": True,
                    "content": generated_content["content"]
                }
                cache.set(cache_key, result)
                return jsonify(result)
        else:
            return jsonify({"success": False, "error": "Failed to generate story"}), 500

    except Exception as e:
        logger.error(f"Error in generate_story: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/suggest_tags", methods=["POST"])
@login_required
@cache.memoize(timeout=300)  # Cache tag suggestions
def suggest_tags():
    """API endpoint to get tag suggestions with caching"""
    try:
        data = request.get_json()
        content = data.get("content", "")
        region = data.get("region", "")

        if not content or not region:
            return jsonify({"success": False, "error": "Missing content or region"}), 400

        # Create a cache key based on content preview and region
        cache_key = f"tags_{region}_{content[:100]}"
        cached_tags = cache.get(cache_key)

        if cached_tags:
            logger.info("Returning cached tag suggestions")
            return jsonify({
                "success": True,
                "tags": cached_tags
            })

        suggested_tags = tag_service.suggest_cultural_tags(content, region)
        cache.set(cache_key, suggested_tags)

        return jsonify({
            "success": True,
            "tags": suggested_tags
        })
    except Exception as e:
        logger.error(f"Error suggesting tags: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/cultural-insights", methods=["POST"])
@login_required
@cache.memoize(timeout=300)  # Cache insights for 5 minutes
def get_cultural_insights():
    """Get cultural context insights for a story"""
    try:
        data = request.get_json()
        content = data.get("content")
        region = data.get("region")
        theme = data.get("theme")

        if not all([content, region, theme]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        # Create cache key based on content preview
        cache_key = f"insights_{region}_{theme}_{content[:100]}"
        cached_insights = cache.get(cache_key)

        if cached_insights:
            logger.info("Returning cached cultural insights")
            return jsonify(cached_insights)

        # Get cultural insights
        insights = cultural_context_service.analyze_context(content, region, theme)
        if insights["success"]:
            # Get additional learning resources
            resources = cultural_context_service.get_learning_resources(content, region)
            if resources["success"]:
                insights["resources"] = resources["resources"]

            cache.set(cache_key, insights)
            return jsonify(insights)

        return jsonify({"success": False, "error": "Failed to get cultural insights"}), 500

    except Exception as e:
        logger.error(f"Error getting cultural insights: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500