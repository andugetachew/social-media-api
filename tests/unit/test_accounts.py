from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from tests.base import BaseTestCase

User = get_user_model()


class AccountTests(BaseTestCase):
    """Test authentication and account management"""

   
    def register(self, data):
        return self.client.post(reverse("register"), data)

    def login(self, email="user1@test.com", password="testpass123"):
        return self.client.post(
            reverse("login"),
            {"email": email, "password": password},
        )

    def refresh_token(self):
        login_response = self.login()
        return login_response.data["refresh"]

  

    def test_register_user(self):
        response = self.register({
            "email": "newuser@test.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "testpass123",
            "password2": "testpass123",
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["email"], "newuser@test.com")

    def test_register_duplicate_email(self):
        response = self.register({
            "email": "user1@test.com",
            "username": "newuser2",
            "full_name": "Another User",
            "password": "testpass123",
            "password2": "testpass123",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        response = self.register({
            "email": "newemail@test.com",
            "username": "user1",
            "full_name": "Another User",
            "password": "testpass123",
            "password2": "testpass123",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        response = self.register({
            "email": "newuser@test.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "testpass123",
            "password2": "wrongpass",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_email(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_with_username(self):
        response = self.login(email="user1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_invalid_credentials(self):
        response = self.login(password="wrongpass")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_user(self):
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user1@test.com")

    def test_get_current_user_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        refresh = self.refresh_token()

        response = self.client.post(
            reverse("token_refresh"),
            {"refresh": refresh},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_logout(self):
        refresh = self.refresh_token()

        response = self.client.post(
            reverse("logout"),
            {"refresh": refresh},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile(self):
        response = self.client.put(
            reverse("update-profile"),
            {"username": "updated_username", "bio": "This is my updated bio"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user1.refresh_from_db()
        self.assertEqual(self.user1.username, "updated_username")
        self.assertEqual(self.user1.bio, "This is my updated bio")

    def test_update_password(self):
        response = self.client.post(
            reverse("update-password"),
            {"old_password": "testpass123", "new_password": "newpass456"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # verify new password works
        self.client.force_authenticate(user=None)

        login_response = self.login(email="user1@test.com", password="newpass456")
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_update_password_wrong_old(self):
        response = self.client.post(
            reverse("update-password"),
            {"old_password": "wrongpass", "new_password": "newpass456"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_account(self):
        response = self.client.delete(reverse("delete-account"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_active)
        self.assertTrue(self.user1.is_deleted)