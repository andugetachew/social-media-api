# Social Media API Documentation

## Base URL
http://localhost:8000/api

---

## 🔐 Authentication

### Register
POST /auth/register/

```json
{
  "email": "user@example.com",
  "username": "john",
  "password": "pass123",
  "password2": "pass123"
}
Login

POST /auth/login/

{
  "email": "user@example.com",
  "password": "pass123"
}

Response:

{
  "access": "jwt_token",
  "refresh": "jwt_token"
}
📝 Posts
Create Post

POST /posts/

{
  "content": "Hello world"
}
Feed (Paginated)

GET /posts/feed/?page=1

👥 Follow System
POST /follow/{user_id}/
DELETE /unfollow/{user_id}/
GET /followers/{user_id}/
GET /following/{user_id}/
💬 Comments
GET /comments/{post_id}/
POST /comments/{post_id}/
DELETE /comments/{comment_id}/
💬 Chat (WebSocket)

ws://localhost:8000/ws/chat/{room_id}/

{
  "message": "Hello"
}
🔔 Notifications

GET /notifications/

POST /notifications/{id}/read/

⚡ Rate Limits
Posts: 50/hour
Likes: 200/hour
Comments: 100/hour
Follows: 100/hour
❌ Error Format
{
  "detail": "Error message"
}
🔐 Authentication Header

Authorization: Bearer <token>