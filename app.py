import os
import logging
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_caching import Cache
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from database import db
from services.service_registry import service_registry

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__)

# App configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
if app.config["SQLALCHEMY_DATABASE_URI"] and app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Configure caching
app.config["CACHE_TYPE"] = "simple"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300
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
    try:
        from services.audio_service import AudioService
        from services.image_service import ImageService
        from services.storage_service import StorageService
        from services.badge_service import BadgeService
        from services.story_service import StoryService
        from services.tag_service import TagService
        from services.cultural_context_service import CulturalContextService
        from services.export_service import ExportService

        # Register all services
        service_registry.register_service('audio', AudioService)
        service_registry.register_service('image', ImageService)
        service_registry.register_service('storage', StorageService)
        service_registry.register_service('badge', BadgeService)
        service_registry.register_service('story', StoryService)
        service_registry.register_service('tag', TagService)
        service_registry.register_service('cultural_context', CulturalContextService)
        service_registry.register_service('export', ExportService)

        logger.info("All services registered")
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")

# Import models after db initialization
try:
    from models import User, Story, Comment, StoryLike, Tag, Badge, UserBadge, EmojiReaction
except Exception as e:
    logger.error(f"Error importing models: {str(e)}")
    raise

# Initialize all services
init_services()

# Initialize database and create default badges
with app.app_context():
    try:
        db.create_all()
        badge_service = service_registry.get_service('badge')
        if badge_service and badge_service.is_available:
            badge_service.initialize_default_badges()
            logger.info("Database and badges initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

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

        # Add debug logging
        app.logger.debug(f"Featured stories count: {len(featured_stories)}")
        app.logger.debug(f"Recent stories count: {len(recent_stories)}")

        return render_template(
            "index.html",
            featured_stories=featured_stories,
            recent_stories=recent_stories
        )
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
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
                user_id=current_user.id,
                submission_date=datetime.datetime.utcnow()
            )
            db.session.add(story)
            db.session.flush()

            # Handle media upload if provided
            if "media" in request.files:
                file = request.files["media"]
                if file.filename:
                    try:
                        file_data = file.read()
                        storage_service = service_registry.get_service('storage')
                        if storage_service and storage_service.is_available:
                            upload_result = storage_service.upload_media(file_data)
                            if upload_result:
                                story.media_url = upload_result["url"]
                        else:
                            logger.error("Storage service is not available")
                            flash("Error uploading media: Storage service unavailable", "error")
                    except Exception as e:
                        logger.error(f"Error uploading media: {str(e)}")
                        flash("Error uploading media", "error")

            # Generate and store AI image if requested
            if generate_image:
                image_service = service_registry.get_service('image')
                if image_service and image_service.is_available:
                    try:
                        logger.info("Generating AI image for story")
                        image_prompt = f"Create an illustration for '{title}': {content[:200]}..."
                        image_result = image_service.generate_image(image_prompt)
                        if image_result["success"]:
                            story.generated_image_url = image_result["url"]
                            logger.info(f"Successfully generated image: {image_result['url']}")
                        else:
                            logger.error(f"Failed to generate image: {image_result.get('error')}")
                            flash("Could not generate AI image: " + image_result.get('error', 'Unknown error'), "warning")
                    except Exception as e:
                        logger.error(f"Error in image generation process: {str(e)}")
                        flash("Error generating AI image", "error")

            # Generate and store audio narration if requested
            if generate_audio:
                audio_service = service_registry.get_service('audio')
                if audio_service and audio_service.is_available:
                    try:
                        logger.info("Generating audio narration")
                        audio_result = audio_service.generate_audio(content)
                        if audio_result["success"]:
                            audio_data = audio_result["audio_data"]
                            storage_service = service_registry.get_service('storage')
                            if storage_service and storage_service.is_available:
                                upload_result = storage_service.upload_media(
                                    audio_data,
                                    resource_type="audio",
                                    public_id=f"audio_{datetime.datetime.utcnow().timestamp()}"
                                )
                                if upload_result and "url" in upload_result:
                                    story.audio_url = upload_result["url"]
                                    logger.info(f"Successfully generated audio: {upload_result['url']}")
                                else:
                                    logger.error("Failed to upload audio: No URL returned")
                                    flash("Could not save audio narration", "warning")
                            else:
                                logger.error("Storage service is not available")
                                flash("Could not save audio narration: Storage service unavailable", "warning")
                        else:
                            logger.error(f"Failed to generate audio: {audio_result.get('error')}")
                            flash(f"Could not generate audio narration: {audio_result.get('error')}", "warning")
                    except Exception as e:
                        logger.error(f"Error generating audio: {str(e)}")
                        flash("Error generating audio narration", "error")

            # Process tags with cultural suggestions
            if tags_input or content:
                try:
                    user_tags = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                    suggested_tags = []
                    tag_service = service_registry.get_service('tag')
                    if content and tag_service and tag_service.is_available:
                        suggested_tags = tag_service.suggest_cultural_tags(content, region)
                    all_tags = list(set(user_tags + suggested_tags))
                    for tag_name in all_tags:
                        tag = tag_service.create_or_get_tag(tag_name)
                        if tag and tag not in story.tags:
                            story.tags.append(tag)
                except Exception as e:
                    logger.error(f"Error processing tags: {str(e)}")
                    flash("Error processing tags", "error")

            # Commit all changes
            try:
                db.session.commit()
                logger.info(f"Successfully saved story with ID: {story.id}")
                flash("Your story has been submitted successfully!", "success")

                # Check for new badges
                badge_service = service_registry.get_service('badge')
                if badge_service and badge_service.is_available:
                    new_badges = badge_service.check_and_award_badges(current_user)
                    if new_badges:
                        badge_names = [badge.name for badge in new_badges]
                        flash(f"Congratulations! You earned new badges: {', '.join(badge_names)}", "success")
                else:
                    logger.error("Badge service is not available")

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

@app.route("/api/react/<int:story_id>", methods=["POST"])
@login_required
def react_to_story(story_id):
    """Add or remove an emoji reaction to a story"""
    try:
        story = Story.query.get_or_404(story_id)
        data = request.get_json()
        emoji = data.get('emoji')

        if not emoji:
            return jsonify({"success": False, "error": "No emoji provided"}), 400

        # Check if user already reacted with this emoji
        existing_reaction = EmojiReaction.query.filter_by(
            story_id=story_id,
            user_id=current_user.id,
            emoji=emoji
        ).first()

        if existing_reaction:
            # Remove reaction if it exists
            db.session.delete(existing_reaction)
            action = 'removed'
        else:
            # Add new reaction
            reaction = EmojiReaction(
                story_id=story_id,
                user_id=current_user.id,
                emoji=emoji
            )
            db.session.add(reaction)
            action = 'added'

        db.session.commit()

        # Get updated reaction counts
        reaction_counts = db.session.query(
            EmojiReaction.emoji, 
            db.func.count(EmojiReaction.id)
        ).filter_by(story_id=story_id).group_by(EmojiReaction.emoji).all()

        return jsonify({
            "success": True,
            "action": action,
            "reactions": dict(reaction_counts)
        })

    except Exception as e:
        app.logger.error(f"Error handling emoji reaction: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/reactions/<int:story_id>")
def get_story_reactions(story_id):
    """Get all emoji reactions for a story"""
    try:
        # Get reaction counts
        reaction_counts = db.session.query(
            EmojiReaction.emoji, 
            db.func.count(EmojiReaction.id)
        ).filter_by(story_id=story_id).group_by(EmojiReaction.emoji).all()

        # Get user's reactions if logged in
        user_reactions = []
        if current_user.is_authenticated:
            user_reactions = [r.emoji for r in EmojiReaction.query.filter_by(
                story_id=story_id,
                user_id=current_user.id
            ).all()]

        return jsonify({
            "success": True,
            "reactions": dict(reaction_counts),
            "userReactions": user_reactions
        })

    except Exception as e:
        app.logger.error(f"Error getting story reactions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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

        story_service = service_registry.get_service('story')
        if story_service and story_service.is_available:
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

        tag_service = service_registry.get_service('tag')
        if tag_service and tag_service.is_available:
            suggested_tags = tag_service.suggest_cultural_tags(content, region)
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

        cultural_context_service = service_registry.get_service('cultural_context')
        if cultural_context_service and cultural_context_service.is_available:
            # Get cultural insights
            insights = cultural_context_service.analyze_context(content, region, theme)
            if insights["success"]:
                # Get additional learning resources
                resources = cultural_context_service.get_learning_resources(content, region)
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
    audio_service = service_registry.get_service('audio')
    if not audio_service or not audio_service.is_available:
        return jsonify({
            "success": False,
            "error": "Audio service is not available. Please check if ElevenLabs API key is configured."
        }), 503

    try:
        data = request.get_json()
        content = data.get("content")
        voice_name = data.get("voice", "Aria")  # Default to Aria instead of Bella

        if not content:
            return jsonify({
                "success": False,
                "error": "Missing content"
            }), 400

        # Generate audio
        audio_result = audio_service.generate_audio(content, voice_name)

        if audio_result["success"]:
            # Upload the audio file
            try:
                audio_data = audio_result["audio_data"]
                storage_service = service_registry.get_service('storage')
                if storage_service and storage_service.is_available:
                    upload_result = storage_service.upload_media(
                        audio_data,
                        resource_type="audio",
                        public_id=f"audio_{datetime.datetime.utcnow().timestamp()}"
                    )

                    if upload_result and "url" in upload_result:
                        logger.info(f"Successfully generated and uploaded audio: {upload_result['url']}")
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

        image_service = service_registry.get_service('image')
        if image_service and image_service.is_available:
            # Generate image
            image_result = image_service.generate_image(image_prompt)

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

@app.route("/story/<int:story_id>")
def view_story(story_id):
    """View a single story, used for social media sharing"""
    story = Story.query.get_or_404(story_id)
    return render_template("view_story.html", story=story)


@app.route("/export/<int:story_id>/<format>")
@login_required
def export_story(story_id, format):
    """Export story in the specified format"""
    story = Story.query.get_or_404(story_id)

    # Check if user has permission to export
    if story.user_id != current_user.id and not current_user.is_admin:
        flash("You don't have permission to export this story", "error")
        return redirect(url_for('view_story', story_id=story_id))

    export_service = service_registry.get_service('export')
    if not export_service or not export_service.is_available:
        flash("Export service is not available", "error")
        return redirect(url_for('view_story', story_id=story_id))

    try:
        if format == 'pdf':
            file_path = export_service.export_to_pdf(story)
            mime_type = 'application/pdf'
        elif format == 'epub':
            file_path = export_service.export_to_epub(story)
            mime_type = 'application/epub+zip'
        elif format == 'txt':
            file_path = export_service.export_to_txt(story)
            mime_type = 'text/plain'
        else:
            flash("Unsupported export format", "error")
            return redirect(url_for('view_story', story_id=story_id))

        if not file_path:
            flash(f"Error exporting story to {format.upper()}", "error")
            return redirect(url_for('view_story', story_id=story_id))

        def after_this_request(f):
            @wraps(f)
            def decorator(*args, **kwargs):
                resp = f(*args, **kwargs)
                resp.call_on_close(remove_file)
                return resp
            return decorator


        response = send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=f"{story.title.lower().replace(' ', '_')}.{format}"
        )

        # Delete temporary file after sending
        @after_this_request
        def remove_file(response):
            try:
                os.unlink(file_path)
            except Exception as e:
                app.logger.error(f"Error removing temporary file: {str(e)}")
            return response

        return response

    except Exception as e:
        app.logger.error(f"Error exporting story: {str(e)}")
        flash("Error exporting story", "error")
        return redirect(url_for('view_story', story_id=story_id))