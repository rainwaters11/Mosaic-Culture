"""Badge management service"""
import logging
from typing import List, Optional
from models import Badge, UserBadge, User
from database import db

logger = logging.getLogger(__name__)

class BadgeService:
    @staticmethod
    def check_and_award_badges(user: User) -> List[Badge]:
        """
        Check if user qualifies for new badges and award them
        Returns list of newly awarded badges
        """
        logger.debug(f"Checking badges for user {user.username}")
        awarded_badges = []
        all_badges = Badge.query.all()
        logger.debug(f"Found {len(all_badges)} total badges to check")

        for badge in all_badges:
            # Skip if user already has this badge
            if any(ub.badge_id == badge.id for ub in user.badges):
                logger.debug(f"User already has badge: {badge.name}")
                continue

            # Check badge requirements
            requirement_type, value = badge.requirement.split(':')
            value = int(value)
            logger.debug(f"Checking requirement {requirement_type}:{value}")

            if requirement_type == 'stories_count':
                if len(user.stories) >= value:
                    logger.info(f"Awarding {badge.name} to {user.username} for stories_count")
                    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                    db.session.add(user_badge)
                    awarded_badges.append(badge)

            elif requirement_type == 'likes_received':
                likes_count = sum(len(story.likes) for story in user.stories)
                if likes_count >= value:
                    logger.info(f"Awarding {badge.name} to {user.username} for likes_received")
                    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                    db.session.add(user_badge)
                    awarded_badges.append(badge)

            elif requirement_type == 'comments_received':
                comments_count = sum(len(story.comments) for story in user.stories)
                if comments_count >= value:
                    logger.info(f"Awarding {badge.name} to {user.username} for comments_received")
                    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                    db.session.add(user_badge)
                    awarded_badges.append(badge)

        if awarded_badges:
            logger.info(f"Awarded {len(awarded_badges)} new badges to {user.username}")
            db.session.commit()

        return awarded_badges

    @staticmethod
    def get_user_badges(user: User) -> List[Badge]:
        """Get all badges earned by a user"""
        logger.debug(f"Getting badges for user {user.username}")
        badges = [ub.badge for ub in user.badges]
        logger.debug(f"Found {len(badges)} badges")
        return badges

    @staticmethod
    def initialize_default_badges():
        """Create default badges if they don't exist"""
        logger.info("Initializing default badges")
        default_badges = [
            {
                'name': 'Storyteller Novice',
                'description': 'Share your first story',
                'icon': 'feather-book',
                'requirement': 'stories_count:1'
            },
            {
                'name': 'Prolific Author',
                'description': 'Share 5 stories',
                'icon': 'feather-books',
                'requirement': 'stories_count:5'
            },
            {
                'name': 'Community Favorite',
                'description': 'Receive 10 likes on your stories',
                'icon': 'feather-heart',
                'requirement': 'likes_received:10'
            },
            {
                'name': 'Conversation Starter',
                'description': 'Receive 5 comments on your stories',
                'icon': 'feather-message-circle',
                'requirement': 'comments_received:5'
            }
        ]

        for badge_data in default_badges:
            if not Badge.query.filter_by(name=badge_data['name']).first():
                logger.info(f"Creating badge: {badge_data['name']}")
                badge = Badge(**badge_data)
                db.session.add(badge)

        db.session.commit()
        logger.info("Default badges initialization complete")