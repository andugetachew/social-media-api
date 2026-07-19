from typing import Dict

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserService:
    """
    Handles user authentication logic.

    NOTE: LoginView currently reimplements login inline rather than calling
    this service, and had already diverged from it in several ways (see
    fixes below). If LoginView is ever refactored to delegate here, this
    now matches its corrected behavior. If nothing calls this method,
    consider removing it entirely rather than maintaining two login code
    paths — duplicated auth logic is how the two drifted apart in the
    first place.
    """

    @staticmethod
    def login_user(email_or_username: str, password: str) -> Dict:
        """Authenticate user and return tokens."""
        try:
            if "@" in email_or_username:
                user = User.objects.get(email=email_or_username)
            else:
                user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
          
            raise ValueError("Invalid credentials")

        if not user.check_password(password):
            raise ValueError("Invalid credentials")

    
        if not user.is_active:
            raise ValueError("Invalid credentials")

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
            },
        }