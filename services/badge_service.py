"""Badge management service"""
from typing import List, Optional
from models import Badge, UserBadge, User
from database import db

class BadgeService:
    @staticmethod
    def check_and_award_badges(user: User) -> List[Badge]:
        """
        Check if user qualifies for new badges and award them
        Returns list of newly awarded badges
        """
        awarded_badges = []
        all_badges = Badge.query.all()

        for badge in all_badges:
            # Skip if user already has this badge
            if any(ub.badge_id == badge.id for ub in user.badges):
                continue

            # Check badge requirements
            requirement_type, value = badge.requirement.split(':')
            value = int(value)

            if requirement_type == 'stories_count':
                if len(user.stories) >= value:
                    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                    db.session.add(user_badge)
                    awarded_badges.append(badge)

            elif requirement_type == 'likes_received':
                likes_count = sum(len(story.likes) for story in user.stories)
                if likes_count >= value:
                    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                    db.session.add(user_badge)
                    awarded_badges.append(badge)

            elif requirement_type == 'comments_received':
                comments_count = sum(len(story.comments) for story in user.stories)
                if comments_count >= value:
                    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
                    db.session.add(user_badge)
                    awarded_badges.append(badge)

        if awarded_badges:
            db.session.commit()

        return awarded_badges

    @staticmethod
    def get_user_badges(user: User) -> List[Badge]:
        """Get all badges earned by a user"""
        return [ub.badge for ub in user.badges]

    @staticmethod
    def initialize_default_badges():
        """Create default badges if they don't exist"""
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
                badge = Badge(**badge_data)
                db.session.add(badge)

        db.session.commit()