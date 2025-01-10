import os
import logging
import io
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
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
from services.export_service import ExportService

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
def init_services():
    """Initialize all services and handle any initialization errors gracefully"""
    services = {}
    try:
        services['export'] = ExportService()
        logger.info("Export service initialized")
    except Exception as e:
        logger.error(f"Error initializing export service: {str(e)}")
        services['export'] = None

    try:
        services['audio'] = AudioService()
        logger.info("Audio service initialized")
    except Exception as e:
        logger.error(f"Error initializing audio service: {str(e)}")
        services['audio'] = None

    try:
        services['image'] = ImageService()
        logger.info("Image service initialized")
    except Exception as e:
        logger.error(f"Error initializing image service: {str(e)}")
        services['image'] = None

    try:
        services['storage'] = StorageService()
        logger.info("Storage service initialized")
    except Exception as e:
        logger.error(f"Error initializing storage service: {str(e)}")
        services['storage'] = None

    try:
        services['badge'] = BadgeService()
        logger.info("Badge service initialized")
    except Exception as e:
        logger.error(f"Error initializing badge service: {str(e)}")
        services['badge'] = None

    try:
        services['story'] = StoryService()
        logger.info("Story service initialized")
    except Exception as e:
        logger.error(f"Error initializing story service: {str(e)}")
        services['story'] = None

    try:
        services['tag'] = TagService()
        logger.info("Tag service initialized")
    except Exception as e:
        logger.error(f"Error initializing tag service: {str(e)}")
        services['tag'] = None

    try:
        services['cultural_context'] = CulturalContextService()
        logger.info("Cultural context service initialized")
    except Exception as e:
        logger.error(f"Error initializing cultural context service: {str(e)}")
        services['cultural_context'] = None

    return services

# Initialize all services
services = init_services()

# Import models after db initialization
from models import User, Story, Comment, StoryLike, Tag, Badge, UserBadge

# Initialize database and create default badges
logger.info("Initializing database and default badges...")
with app.app_context():
    try:
        db.create_all()
        if services['badge']:
            services['badge'].initialize_default_badges()
        logger.info("Database and badges initialized successfully")
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

        # Add debug logging for template context
        app.logger.debug("Index route accessed")
        app.logger.debug(f"Featured stories count: {len(featured_stories)}")
        app.logger.debug(f"Recent stories count: {len(recent_stories)}")

        return render_template(
            "index.html",
            featured_stories=featured_stories,
            recent_stories=recent_stories
        )
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
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
    """Story submission page"""
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        region = request.form.get("region")
        theme = request.form.get("theme")
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
                theme=theme,
                user_id=current_user.id,
                submission_date=datetime.datetime.utcnow()
            )
            db.session.add(story)
            db.session.flush()

            # Process tags
            if tags_input:
                try:
                    user_tags = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                    for tag_name in user_tags:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                        story.tags.append(tag)
                except Exception as e:
                    logger.error(f"Error processing tags: {str(e)}")
                    flash("Error processing tags", "error")

            # Commit changes
            try:
                db.session.commit()
                flash("Your story has been submitted successfully!", "success")
                return redirect(url_for("view_story", story_id=story.id))
            except Exception as e:
                logger.error(f"Error saving story: {str(e)}")
                db.session.rollback()
                flash("Error saving your story", "error")
                return redirect(url_for("submit_story"))

        except Exception as e:
            logger.error(f"Unexpected error in submit_story: {str(e)}")
            flash("An unexpected error occurred", "error")
            return redirect(url_for("submit_story"))

    return render_template("submit.html")

@app.route("/gallery")
def gallery():
    """Gallery page with story listing"""
    try:
        region_filter = request.args.get("region")
        tag_filter = request.args.get("tag")

        query = Story.query.order_by(Story.submission_date.desc())

        if region_filter:
            query = query.filter_by(region=region_filter)

        if tag_filter:
            query = query.join(Story.tags).filter(Tag.name == tag_filter)

        stories = query.all()
        all_tags = Tag.query.order_by(Tag.name).all()

        app.logger.debug(f"Gallery route accessed - Stories count: {len(stories)}")
        return render_template("gallery.html", stories=stories, all_tags=all_tags)
    except Exception as e:
        logger.error(f"Error in gallery route: {str(e)}")
        flash("Error loading stories", "error")
        return render_template("gallery.html", stories=[], all_tags=[])

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
    """User profile with their stories and badges"""
    try:
        user_stories = Story.query.filter_by(user_id=current_user.id)\
            .order_by(Story.submission_date.desc()).all()
        user_badges = UserBadge.query.filter_by(user_id=current_user.id).all()

        app.logger.debug(f"User stories count: {len(user_stories)}")
        app.logger.debug(f"User badges count: {len(user_badges)}")

        return render_template(
            "profile.html",
            stories=user_stories,
            badges=user_badges
        )
    except Exception as e:
        app.logger.error(f"Error in profile route: {str(e)}")
        flash("Error loading profile data", "error")
        return render_template("profile.html", stories=[], badges=[])

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

        if services['story']:
            generated_content = services['story'].generate_story(title, theme, region)
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
        else:
            logger.error("Story service is not available")
            return jsonify({"success": False, "error": "Story service unavailable"}), 503

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

        if services['tag']:
            suggested_tags = services['tag'].suggest_cultural_tags(content, region)
            cache.set(cache_key, suggested_tags)
            return jsonify({
                "success": True,
                "tags": suggested_tags
            })
        else:
            logger.error("Tag service is not available")
            return jsonify({"success": False, "error": "Tag service unavailable"}), 503


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

        if services['cultural_context']:
            # Get cultural insights
            insights = services['cultural_context'].analyze_context(content, region, theme)
            if insights["success"]:
                # Get additional learning resources
                resources = services['cultural_context'].get_learning_resources(content, region)
                if resources["success"]:
                    insights["resources"] = resources["resources"]

                cache.set(cache_key, insights)
                return jsonify(insights)
            else:
                return jsonify({"success": False, "error": "Failed to get cultural insights"}), 500
        else:
            logger.error("Cultural context service is not available")
            return jsonify({"success": False, "error": "Cultural context service unavailable"}), 503

    except Exception as e:
        logger.error(f"Error getting cultural insights: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/generate-audio", methods=["POST"])
@login_required
def generate_audio():
    """API endpoint to generate audio narration using ElevenLabs"""
    if not services['audio'] or not services['audio'].is_available:
        return jsonify({
            "success": False,
            "error": "Audio service is not available. Please check if ElevenLabs API key is configured."
        }), 503

    try:
        data = request.get_json()
        story_id = data.get("story_id")
        voice_name = data.get("voice", "Aria")  # Default to Aria voice

        # Get voice customization parameters
        stability = float(data.get("stability", 0.75))
        similarity_boost = float(data.get("similarity_boost", 0.75))
        style = float(data.get("style", 0.0))
        speaking_rate = float(data.get("speaking_rate", 1.0))
        pitch = float(data.get("pitch", 0.0))

        # Fetch the story
        story = Story.query.get_or_404(story_id)

        if not story.content:
            return jsonify({
                "success": False,
                "error": "Story content is missing"
            }), 400

        # Check if audio already exists
        if story.audio_url:
            return jsonify({
                "success": True,
                "audio_url": story.audio_url,
                "message": "Audio already exists"
            })

        # Generate audio with customized voice settings
        audio_result = services['audio'].generate_audio(
            story.content,
            voice_name=voice_name,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            speaking_rate=speaking_rate,
            pitch=pitch
        )

        if audio_result["success"]:
            try:
                audio_data = audio_result["audio_data"]
                if services['storage']:
                    # Upload the audio file to storage
                    upload_result = services['storage'].upload_media(
                        audio_data,
                        resource_type="audio",
                        public_id=f"audio_{story_id}_{datetime.datetime.utcnow().timestamp()}"
                    )

                    if upload_result and "url" in upload_result:
                        # Save the audio URL to the story
                        story.audio_url = upload_result["url"]
                        db.session.commit()

                        logger.info(f"Successfully generated and uploaded audio for story {story_id}")
                        return jsonify({
                            "success": True,
                            "audio_url": upload_result["url"]
                        })
                    else:
                        raise Exception("Failed to upload audio file")
                else:
                    raise Exception("Storage service is not available")

            except Exception as e:
                logger.error(f"Error uploading audio: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Error uploading audio: {str(e)}"
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": audio_result.get("error", "Unknown error occurred")
            }), 500

    except Exception as e:
        logger.error(f"Error in generate_audio endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/generate-image", methods=["POST"])
@login_required
def generate_image():
    """API endpoint to generate an image using DALL-E"""
    try:
        data = request.get_json()
        title = data.get("title")
        content = data.get("content")

        if not title or not content:
            return jsonify({
                "success": False,
                "error": "Missing title or content"
            }), 400

        # Create image prompt
        image_prompt = f"Create an illustration for '{title}': {content[:200]}..."
        logger.info(f"Generating image with prompt: {image_prompt}")

        if services['image']:
            # Generate image
            image_result = services['image'].generate_image(image_prompt)

            if image_result["success"]:
                logger.info(f"Successfully generated image: {image_result['url']}")
                return jsonify({
                    "success": True,
                    "url": image_result["url"]
                })

            logger.error(f"Failed to generate image: {image_result.get('error')}")
            return jsonify({
                "success": False,
                "error": image_result.get("error", "Failed to generate image")
            }), 500
        else:
            logger.error("Image service is not available")
            return jsonify({"success": False, "error": "Image service unavailable"}), 503

    except Exception as e:
        logger.error(f"Error in generate_image endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/story/<int:story_id>", methods=["GET"])
def view_story(story_id):
    """View a single story with audio generation capabilities"""
    try:
        story = Story.query.get_or_404(story_id)
        return render_template("view_story.html", story=story)
    except Exception as e:
        logger.error(f"Error viewing story {story_id}: {str(e)}")
        flash("Error loading story", "error")
        return redirect(url_for("gallery"))


@app.route("/story/<int:story_id>/export/<format>")
def export_story(story_id, format):
    """Export story in various formats"""
    try:
        story = Story.query.get_or_404(story_id)

        if format not in services['export'].supported_formats:
            return jsonify({
                "success": False,
                "error": "Unsupported format"
            }), 400

        if not services['export']:
            return jsonify({
                "success": False,
                "error": "Export service unavailable"
            }), 503

        # Generate appropriate filename
        filename = f"{story.title.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}"

        if format == 'pdf':
            # Render template for PDF
            html_content = render_template(
                'story_export.html',
                story=story
            )
            pdf_data = services['export'].export_to_pdf(story, html_content)
            if pdf_data:
                return send_file(
                    io.BytesIO(pdf_data),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"{filename}.pdf"
                )

        elif format == 'epub':
            epub_data = services['export'].export_to_epub(story)
            if epub_data:
                return send_file(
                    io.BytesIO(epub_data),
                    mimetype='application/epub+zip',
                    as_attachment=True,
                    download_name=f"{filename}.epub"
                )

        elif format == 'txt':
            txt_data = services['export'].export_to_txt(story)
            if txt_data:
                return send_file(
                    io.BytesIO(txt_data),
                    mimetype='text/plain',
                    as_attachment=True,
                    download_name=f"{filename}.txt"
                )

        elif format == 'json':
            json_data = services['export'].export_to_json(story)
            if json_data:
                return send_file(
                    io.BytesIO(json_data),
                    mimetype='application/json',
                    as_attachment=True,
                    download_name=f"{filename}.json"
                )

        return jsonify({
            "success": False,
            "error": "Failed to generate export"
        }), 500

    except Exception as e:
        logger.error(f"Error exporting story: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500