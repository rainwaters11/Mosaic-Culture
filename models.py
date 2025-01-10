from database import db
from flask_login import UserMixin
import datetime

# Story-Tag Association Table
story_tags = db.Table('story_tags',
    db.Column('story_id', db.Integer, db.ForeignKey('stories.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
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

class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    region = db.Column(db.String(100), nullable=False)
    media_url = db.Column(db.String(500))  # URL for uploaded media (Cloudinary)
    generated_image_url = db.Column(db.String(500))  # URL for DALL-E generated image
    audio_url = db.Column(db.String(500))  # URL for ElevenLabs generated audio
    submission_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    likes = db.relationship('StoryLike', backref='story', lazy=True)
    comments = db.relationship('Comment', backref='story', lazy=True)
    tags = db.relationship('Tag', secondary=story_tags, lazy='subquery',
        backref=db.backref('stories', lazy=True))

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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