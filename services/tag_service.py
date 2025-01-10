"""Tag management service"""
import logging
from typing import List, Optional
from models import Tag, Story
from database import db

logger = logging.getLogger(__name__)

class TagService:
    @staticmethod
    def create_or_get_tag(name: str, category: str = "general") -> Tag:
        """
        Create a new tag or get existing one
        Args:
            name: The tag name
            category: Cultural category (e.g., tradition, ritual, cuisine)
        Returns the tag object
        """
        try:
            tag = Tag.query.filter_by(name=name.lower()).first()
            if not tag:
                tag = Tag(name=name.lower(), category=category)
                db.session.add(tag)
                db.session.commit()
                logger.info(f"Created new tag: {name} in category {category}")
            return tag
        except Exception as e:
            logger.error(f"Error creating/getting tag: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def get_popular_tags(limit: int = 10) -> List[Tag]:
        """Get most frequently used tags"""
        try:
            # Query tags and count their usage
            popular_tags = (
                db.session.query(Tag, db.func.count(Story.id).label('story_count'))
                .join(Story.tags)
                .group_by(Tag)
                .order_by(db.desc('story_count'))
                .limit(limit)
                .all()
            )
            return [tag for tag, _ in popular_tags]
        except Exception as e:
            logger.error(f"Error getting popular tags: {str(e)}")
            return []

    @staticmethod
    def get_tags_by_category(category: str) -> List[Tag]:
        """Get tags filtered by cultural category"""
        try:
            return Tag.query.filter_by(category=category).order_by(Tag.name).all()
        except Exception as e:
            logger.error(f"Error getting tags by category: {str(e)}")
            return []

    @staticmethod
    def suggest_cultural_tags(story_content: str, region: str) -> List[str]:
        """
        Suggest culturally relevant tags based on story content
        Returns list of suggested tag names
        """
        try:
            from openai import OpenAI
            import os
            import json

            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            
            prompt = (
                f"Analyze this story from {region} and suggest relevant cultural tags.\n\n"
                f"Story: {story_content[:500]}...\n\n"
                "Return a JSON array of tag names focusing on cultural elements like:\n"
                "- Traditional practices\n"
                "- Cultural symbols\n"
                "- Customs and rituals\n"
                "- Regional specialties\n"
                "- Historical references"
            )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a cultural tagging expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            suggestions = json.loads(response.choices[0].message.content)
            return suggestions.get("tags", [])

        except Exception as e:
            logger.error(f"Error suggesting cultural tags: {str(e)}")
            return []
