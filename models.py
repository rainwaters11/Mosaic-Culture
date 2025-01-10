from database import db
from flask_login import UserMixin
import datetime

# Story-Tag Association Table
story_tags = db.Table('story_tags',
    db.Column('story_id', db.Integer, db.ForeignKey('stories.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class EmojiReaction(db.Model):
    """Model for storing emoji reactions on stories"""
    __tablename__ = 'emoji_reactions'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(50), nullable=False)  # Store emoji unicode or name
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Add unique constraint to prevent multiple reactions of same type from same user
    __table_args__ = (
        db.UniqueConstraint('story_id', 'user_id', 'emoji', name='unique_user_emoji_reaction'),
    )

class Badge(db.Model):
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    icon = db.Column(db.String(100), nullable=False)  # SVG icon path
    requirement = db.Column(db.String(100), nullable=False)  # e.g., "stories_count:5"
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    badge = db.relationship('Badge', backref='user_badges')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    comments = db.relationship('Comment', backref='author', lazy=True)
    badges = db.relationship('UserBadge', backref='user', lazy=True)
    stories = db.relationship('Story', backref='author', lazy=True)
    emoji_reactions = db.relationship('EmojiReaction', backref='user', lazy=True)

class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    region = db.Column(db.String(100), nullable=False)
    media_url = db.Column(db.String(500))  # URL for uploaded media (Cloudinary)
    generated_image_url = db.Column(db.String(500))  # URL for DALL-E generated image
    audio_url = db.Column(db.String(500))  # URL for ElevenLabs generated audio
    soundtrack_url = db.Column(db.String(500))  # URL for generated soundtrack
    submission_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    likes = db.relationship('StoryLike', backref='story', lazy=True)
    comments = db.relationship('Comment', backref='story', lazy=True)
    tags = db.relationship('Tag', secondary=story_tags, lazy='subquery',
        backref=db.backref('stories', lazy=True))
    emoji_reactions = db.relationship('EmojiReaction', backref='story', lazy=True)
    is_featured = db.Column(db.Boolean, default=False)  # New column for featured status
    featured_date = db.Column(db.DateTime)  # New column to track when story was featured

    @classmethod
    def get_featured_stories(cls, limit=5):
        """Get the most recent featured stories"""
        return cls.query.filter_by(is_featured=True)\
                      .order_by(cls.featured_date.desc())\
                      .limit(limit)\
                      .all()

    @classmethod
    def get_trending_stories(cls, limit=5):
        """Get stories with the most engagement (likes + comments)"""
        return cls.query\
            .join(StoryLike)\
            .group_by(Story.id)\
            .order_by(db.func.count(StoryLike.id).desc())\
            .limit(limit)\
            .all()

    @classmethod
    def get_story_of_the_day(cls):
        """Get a random story for the story of the day feature"""
        from sqlalchemy.sql.expression import func
        # Get a random story that has an image (either uploaded or generated)
        return cls.query\
            .filter(db.or_(
                cls.media_url.isnot(None),
                cls.generated_image_url.isnot(None)
            ))\
            .order_by(func.random())\
            .first()

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50), default='general', nullable=False)  # Added category field
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    description = db.Column(db.String(200))  # Added description field

class StoryLike(db.Model):
    __tablename__ = 'story_likes'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)