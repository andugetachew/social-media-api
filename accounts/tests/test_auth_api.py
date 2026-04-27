from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@test.com", username="testuser", password="testpass123"
        )

    def test_register_user(self):
        """Test user registration"""
        url = reverse("register")
        data = {
            "email": "new@test.com",
            "username": "newuser",
            "password": "testpass123",
            "password2": "testpass123",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)

    def test_register_user_passwords_mismatch(self):
        """Test registration with mismatched passwords"""
        url = reverse("register")
        data = {
            "email": "new@test.com",
            "username": "newuser",
            "password": "testpass123",
            "password2": "wrongpassword",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)

    def test_login_user(self):
        """Test user login"""
        url = reverse("login")
        data = {"email": "test@test.com", "password": "testpass123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        url = reverse("login")
        data = {"email": "wrong@test.com", "password": "wrong"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 401)

    def test_get_me_authenticated(self):
        """Test getting current user when authenticated"""
        self.client.force_authenticate(user=self.user)
        url = reverse("me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "test@test.com")
        self.assertEqual(response.data["username"], "testuser")

    def test_get_me_unauthenticated(self):
        """Test getting current user when not authenticated"""
        url = reverse("me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_refresh_token(self):
        """Test token refresh using SimpleJWT endpoint"""
        # First create a refresh token
        refresh = RefreshToken.for_user(self.user)
        refresh_token = str(refresh)

        # Use SimpleJWT's refresh endpoint
        url = reverse("token_refresh")
        response = self.client.post(url, {"refresh": refresh_token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_logout(self):
        """Test logout (blacklist refresh token)"""
        # First login to get refresh token
        login_url = reverse("login")
        login_data = {"email": "test@test.com", "password": "testpass123"}
        login_response = self.client.post(login_url, login_data)
        refresh_token = login_response.data["refresh"]

        # Logout requires authentication
        self.client.force_authenticate(user=self.user)
        logout_url = reverse("logout")
        response = self.client.post(logout_url, {"refresh": refresh_token})
        self.assertEqual(response.status_code, 200)
