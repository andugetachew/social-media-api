 complete social media API Documentation
Base URL
text
http://127.0.0.1:8000/api
Authentication
All endpoints except /auth/register/, /auth/login/, and /password_reset/ require a Bearer token in the Authorization header:

text
Authorization: Bearer <your_access_token>
🔐 Authentication Endpoints
1. Register User
POST /auth/register/

Request Body:

json
{
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "password": "securepass123",
  "password2": "securepass123"
}
Response (201 Created):

json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe"
  }
}
2. Login
POST /auth/login/

Request Body:

json
{
  "email": "user@example.com",
  "password": "securepass123"
}
Response (200 OK):

json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "bio": "",
    "profile_picture": null,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
3. Refresh Token
POST /auth/refresh/

Request Body:

json
{
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
Response (200 OK):

json
{
  "access": "eyJhbGciOiJIUzI1NiIs..."
}
4. Get Current User
GET /auth/me/

Response (200 OK):

json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "bio": "Software engineer",
  "profile_picture": "/media/profile_pics/avatar.jpg",
  "created_at": "2024-01-15T10:30:00Z"
}
5. Update Profile
PUT /auth/update-profile/

Request Body:

json
{
  "username": "johndoe_new",
  "email": "newemail@example.com",
  "bio": "I love coding!"
}
Response (200 OK):

json
{
  "id": "550e8400...",
  "username": "johndoe_new",
  "email": "newemail@example.com",
  "bio": "I love coding!"
}
6. Update Password
POST /auth/update-password/

Request Body:

json
{
  "old_password": "oldpass123",
  "new_password": "newpass123"
}
Response (200 OK):

json
{
  "message": "Password updated successfully"
}
7. Upload Profile Picture
POST /auth/update-photo/

Request Body: multipart/form-data

text
profile_picture: [file] (image/jpeg, image/png, image/gif)
Response (200 OK):

json
{
  "message": "Profile photo updated",
  "url": "/media/profile_pics/avatar_123.jpg"
}
8. Delete Account
DELETE /auth/delete-account/

Response (200 OK):

json
{
  "message": "Account deleted successfully"
}
9. Update Online Status
POST /auth/online/

Request Body:

json
{
  "is_online": true
}
Response (200 OK):

json
{
  "status": "updated"
}
10. Get User Status
GET /auth/status/{user_id}/

Response (200 OK):

json
{
  "is_online": true,
  "last_seen": "2024-01-15T14:30:00Z"
}
📝 Posts Endpoints
11. Create Post
POST /posts/

Request Body (JSON):

json
{
  "content": "Hello world!"
}
Or with image (multipart/form-data):

text
content: "Hello world!"
image: [file]
Response (201 Created):

json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "content": "Hello world!",
  "image": "/media/posts/image123.jpg",
  "created_at": "2024-01-15T12:00:00Z",
  "author": {
    "id": "550e8400...",
    "username": "johndoe"
  },
  "likes_count": 0,
  "user_liked": false
}
12. Get User's Posts
GET /posts/

Response (200 OK):

json
[
  {
    "id": "660e8400...",
    "content": "First post",
    "created_at": "2024-01-15T12:00:00Z",
    "likes_count": 5,
    "user_liked": false
  }
]
13. Get Feed (Personalized)
GET /posts/feed/?page=1&page_size=10

Response (200 OK):

json
{
  "count": 25,
  "next": "http://127.0.0.1:8000/api/posts/feed/?page=2",
  "previous": null,
  "results": [
    {
      "id": "660e8400...",
      "content": "Post from followed user",
      "created_at": "2024-01-15T13:00:00Z",
      "author": {
        "username": "janedoe"
      },
      "likes_count": 3,
      "user_liked": true
    }
  ]
}
14. Update Post
PUT /posts/{post_id}/update/

Request Body:

json
{
  "content": "Updated content"
}
Response (200 OK): Updated post object

15. Delete Post
DELETE /posts/{post_id}/

Response (204 No Content)

16. Like/Unlike Post
POST /posts/{post_id}/like/

Response (200 OK):

json
{
  "liked": true,
  "likes_count": 42
}
👥 Interactions (Follow System)
17. Follow User
POST /interactions/follow/{user_id}/

Response (201 Created):

json
{
  "followed": true,
  "follower_id": "550e8400...",
  "following_id": "660e8400..."
}
18. Unfollow User
DELETE /interactions/unfollow/{user_id}/

Response (200 OK):

json
{
  "followed": false
}
19. Get Followers
GET /interactions/followers/{user_id}/

Response (200 OK):

json
[
  {
    "id": "770e8400...",
    "username": "follower1",
    "email": "follower@example.com"
  }
]
20. Get Following
GET /interactions/following/{user_id}/

Response (200 OK): Same format as followers

21. Get Follow Stats
GET /interactions/stats/{user_id}/

Response (200 OK):

json
{
  "followers_count": 150,
  "following_count": 75
}
💬 Comments Endpoints
22. Get Comments
GET /comments/post/{post_id}/

Response (200 OK):

json
[
  {
    "id": "880e8400...",
    "content": "Great post!",
    "author": {
      "username": "commenter",
      "id": "990e8400..."
    },
    "created_at": "2024-01-15T14:00:00Z"
  }
]
23. Add Comment
POST /comments/post/{post_id}/

Request Body:

json
{
  "content": "Nice post!"
}
Response (201 Created): Comment object

24. Delete Comment
DELETE /comments/{comment_id}/

Response (200 OK):

json
{
  "message": "Comment deleted"
}
💬 Chat Endpoints
25. Get Chat Rooms
GET /chat/rooms/

Response (200 OK):

json
[
  {
    "id": "aa0e8400...",
    "other_user": {
      "id": "bb0e8400...",
      "username": "janedoe",
      "email": "jane@example.com"
    },
    "last_message": "Hello there!"
  }
]
26. Get Messages with User
GET /chat/messages/{other_user_id}/

Response (200 OK):

json
[
  {
    "id": "cc0e8400...",
    "sender_id": "550e8400...",
    "content": "Hi!",
    "created_at": "2024-01-15T15:00:00Z"
  }
]
27. Upload File
POST /chat/upload/

Request Body: multipart/form-data

text
file: [image, PDF, Word, PPT, or text file]
Response (200 OK):

json
{
  "url": "http://127.0.0.1:8000/media/chat_files/abc123.jpg",
  "filename": "image.jpg",
  "is_image": true,
  "thumbnail_url": "http://127.0.0.1:8000/media/chat_thumbnails/thumb123.jpg",
  "size": 1024000
}
28. Edit Message
PUT /chat/edit/{message_id}/

Request Body:

json
{
  "content": "Edited message"
}
Response (200 OK): Updated message object

29. Delete Message
DELETE /chat/delete/{message_id}/

Response (200 OK):

json
{
  "status": "deleted"
}
30. Typing Indicator
POST /chat/typing/

Request Body:

json
{
  "recipient_id": "550e8400...",
  "is_typing": true
}
Response (200 OK):

json
{
  "status": "ok"
}
31. Get Typing Status
GET /chat/typing/{user_id}/

Response (200 OK):

json
{
  "typing_user_ids": ["550e8400..."]
}
WebSocket Chat Connection
URL: ws://127.0.0.1:8000/ws/chat/{room_id}/

Send Message:

json
{
  "message": "Hello!",
  "sender_id": "550e8400...",
  "recipient_id": "660e8400..."
}
Receive Message:

json
{
  "id": "dd0e8400...",
  "message": "Hello!",
  "sender_id": "550e8400..."
}
🔔 Notifications Endpoints
32. Get Notifications
GET /notifications/

Response (200 OK):

json
[
  {
    "id": "ee0e8400...",
    "notification_type": "like",
    "message": "johndoe liked your post",
    "is_read": false,
    "created_at": "2024-01-15T16:00:00Z"
  }
]
33. Mark Notification as Read
POST /notifications/{notification_id}/read/

Response (200 OK):

json
{
  "status": "marked as read"
}
🔐 Password Reset
34. Request Password Reset
POST /password_reset/

Request Body:

json
{
  "email": "user@example.com"
}
Response (200 OK):

json
{
  "status": "OK"
}
35. Confirm Password Reset
POST /password_reset/confirm/

Request Body:

json
{
  "token": "abc123...",
  "password": "newpassword123"
}
Response (200 OK):

json
{
  "status": "OK"
}
📊 Error Responses
400 Bad Request
json
{
  "error": "Missing required field"
}
401 Unauthorized
json
{
  "error": "Authentication required. Please login."
}
403 Forbidden
json
{
  "error": "You do not have permission to perform this action."
}
404 Not Found
json
{
  "error": "Resource not found"
}
429 Too Many Requests
json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
500 Internal Server Error
json
{
  "error": "Internal server error. Please try again later."
}
📋 HTTP Status Codes
Code	Meaning
200	OK – Request successful
201	Created – Resource created
204	No Content – Deletion successful
400	Bad Request – Invalid input
401	Unauthorized – Missing/invalid token
403	Forbidden – Insufficient permissions
404	Not Found – Resource doesn't exist
429	Too Many Requests – Rate limit exceeded
500	Internal Server Error – Server issue
# Windows CMD Commands

### 1. Register
```cmd
curl -X POST http://127.0.0.1:8000/api/auth/register/ -H "Content-Type: application/json" -d "{\"email\":\"user@test.com\",\"username\":\"user1\",\"full_name\":\"Test User\",\"password\":\"pass123\",\"password2\":\"pass123\"}"
2. Login
cmd
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\"email\":\"user@test.com\",\"password\":\"pass123\"}"
3. Get Profile
cmd
curl -X GET http://127.0.0.1:8000/api/auth/me/ -H "Authorization: Bearer YOUR_TOKEN"
4. Create Post
cmd
curl -X POST http://127.0.0.1:8000/api/posts/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"content\":\"Hello World\"}"
5. Get Feed
cmd
curl -X GET http://127.0.0.1:8000/api/posts/feed/ -H "Authorization: Bearer YOUR_TOKEN"
6. Like Post
cmd
curl -X POST http://127.0.0.1:8000/api/posts/POST_ID/like/ -H "Authorization: Bearer YOUR_TOKEN"
7. Follow User
cmd
curl -X POST http://127.0.0.1:8000/api/interactions/follow/USER_ID/ -H "Authorization: Bearer YOUR_TOKEN"
8. Unfollow User
cmd
curl -X DELETE http://127.0.0.1:8000/api/interactions/unfollow/USER_ID/ -H "Authorization: Bearer YOUR_TOKEN"
9. Add Comment
cmd
curl -X POST http://127.0.0.1:8000/api/comments/post/POST_ID/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"content\":\"Nice post\"}"
10. Get Notifications
cmd
curl -X GET http://127.0.0.1:8000/api/notifications/ -H "Authorization: Bearer YOUR_TOKEN"