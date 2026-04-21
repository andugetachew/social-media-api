from django.db import transaction, IntegrityError
from .models import Follow
from typing import Dict


class FollowService:
    """Handles follow/unfollow logic."""
    
    @staticmethod
    def follow_user(follower_id: str, following_id: str) -> Dict:
        """Follow a user. Cannot follow yourself or follow twice."""
        if follower_id == following_id:
            raise ValueError("You cannot follow yourself")
        
        try:
            with transaction.atomic():
                follow = Follow.objects.create(
                    follower_id=follower_id,
                    following_id=following_id
                )
                
                return {
                    'followed': True,
                    'follower_id': follower_id,
                    'following_id': following_id
                }
        except IntegrityError:
            raise ValueError("Already following this user")
    
    @staticmethod
    def unfollow_user(follower_id: str, following_id: str) -> Dict:
        """Unfollow a user."""
        deleted_count, _ = Follow.objects.filter(
            follower_id=follower_id,
            following_id=following_id
        ).delete()
        
        if deleted_count == 0:
            raise ValueError("Not following this user")
        
        return {'followed': False}
    
    @staticmethod
    def get_follow_stats(user_id: str) -> Dict:
        """Get follower and following counts."""
        return {
            'followers_count': Follow.objects.filter(following_id=user_id).count(),
            'following_count': Follow.objects.filter(follower_id=user_id).count()
        }