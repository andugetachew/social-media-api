from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.test_user = {
            "email": "test@test.com",
            "username": "testuser",
            "password": "testpass123",
            "password2": "testpass123",
        }

    def test_register_user(self):
        response = self.client.post(reverse("register"), self.test_user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)

    def test_login_user(self):
        self.client.post(reverse("register"), self.test_user)
        response = self.client.post(
            reverse("login"), {"email": "test@test.com", "password": "testpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_create_post(self):
        self.client.post(reverse("register"), self.test_user)
        login = self.client.post(
            reverse("login"), {"email": "test@test.com", "password": "testpass123"}
        )
        token = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(reverse("posts"), {"content": "Test post"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_follow_user(self):
        # Create two users
        self.client.post(reverse("register"), self.test_user)
        self.client.post(
            reverse("register"),
            {
                "email": "test2@test.com",
                "username": "testuser2",
                "password": "testpass123",
                "password2": "testpass123",
            },
        )

        # Login as first user
        login = self.client.post(
            reverse("login"), {"email": "test@test.com", "password": "testpass123"}
        )
        token = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Get second user's ID
        user2 = User.objects.get(email="test2@test.com")

        # Follow second user
        response = self.client.post(f"/api/interactions/follow/{user2.id}/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
