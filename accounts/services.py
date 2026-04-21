from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from typing import Dict


class UserService:
    """Handles user authentication logic."""
    
    @staticmethod
    def login_user(email: str, password: str) -> Dict:
        """Authenticate user and return tokens."""
        user = authenticate(email=email, password=password)
        
        if not user:
            raise ValueError("Invalid credentials")
        
        if not user.is_active:
            raise ValueError("Account is disabled")
        
        refresh = RefreshToken.for_user(user)
        
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username
            }
        }