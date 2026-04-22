# Social Media API

A production-ready social media platform backend built with Django REST Framework, featuring JWT authentication, real-time feed, Celery background tasks, WebSocket chat, and PostgreSQL.

## 🚀 Features

### Core Features
- **JWT Authentication** – Register, login, refresh tokens
- **Posts** – Create, read, update, delete posts with images
- **Comments** – Add, delete, list comments
- **Likes** – Like/unlike posts with real-time counts
- **Follow System** – Follow/unfollow users, view followers/following
- **Personalized Feed** – Posts from users you follow + your own posts
- **Search** – Search users by username
- **Pagination** – 10 posts per page with load more

### Real‑time Chat
- **WebSocket Chat** – Real‑time messaging between users
- **Online/Offline Status** – Green dot with last seen
- **Typing Indicator** – Shows when the other user is typing
- **Edit & Delete Messages** – Only the sender can modify
- **File Upload** – Images (preview), PDF, Word, PowerPoint, text

### Advanced Features
- **Background Notifications** – Celery fan-out for followers (async)
- **Background Moderation** – Toxicity check for posts
- **Image Upload** – Profile pictures & post images with thumbnails
- **Email Verification** – Confirm email addresses
- **Forgot Password** – Email‑based password reset
- **Rate Limiting** – Prevent spam (50 posts/hour, 200 likes/hour)
- **Logging** – Error logging to `logs/django.log`
- **Swagger Documentation** – Auto‑generated API docs
- **Admin Panel** – Full moderation interface

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 6.0, Django REST Framework |
| Database | PostgreSQL |
| Task Queue | Celery, Redis |
| WebSocket | Django Channels, Redis |
| Authentication | JWT (SimpleJWT) |
| Image Processing | Pillow |
| Documentation | drf-yasg (Swagger) |
| Frontend | React + Tailwind CSS (separate repo) |

## 📦 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis

### Backend Setup

```bash
# Clone repository
git clone https://github.com/andugetachew/social-media-api.git
cd social-media-api

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create PostgreSQL database
psql -U postgres
CREATE DATABASE social_media_db;
\q

# Create .env file
echo SECRET_KEY=your-secret-key-here > .env
echo DB_NAME=social_media_db >> .env
echo DB_USER=postgres >> .env
echo DB_PASSWORD=postgres >> .env
echo DB_HOST=localhost >> .env
echo DB_PORT=5432 >> .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run Daphne (ASGI server for WebSockets)
daphne -p 8000 config.asgi:application
Run Celery (Background Tasks)
bash
# Terminal 2 – Start Redis (Docker)
docker run -d -p 6379:6379 --name redis redis

# Terminal 3 – Start Celery worker
celery -A config worker --loglevel=info --pool=solo
📡 API Endpoints
Method	Endpoint	Description
POST	/api/auth/register/	Register new user
POST	/api/auth/login/	Login (returns JWT)
POST	/api/auth/refresh/	Refresh access token
GET	/api/auth/me/	Get current user
GET	/api/posts/	Get user's posts
POST	/api/posts/	Create new post
PUT	/api/posts/{id}/update/	Update post
DELETE	/api/posts/{id}/	Delete post
GET	/api/posts/feed/	Get personalized feed
POST	/api/posts/{id}/like/	Like/unlike post
POST	/api/interactions/follow/{id}/	Follow user
DELETE	/api/interactions/unfollow/{id}/	Unfollow user
GET	/api/comments/post/{id}/	Get post comments
POST	/api/comments/post/{id}/	Add comment
GET	/api/notifications/	Get notifications
WS	ws://127.0.0.1:8000/ws/chat/{room_id}/	WebSocket chat connection
📚 API Documentation
Once running, visit:

Swagger UI: http://127.0.0.1:8000/swagger/

ReDoc: http://127.0.0.1:8000/redoc/

Admin Panel: http://127.0.0.1:8000/admin

🔒 Environment Variables
Variable	Description
SECRET_KEY	Django secret key
DB_NAME	Database name
DB_USER	Database user
DB_PASSWORD	Database password
DB_HOST	Database host
DB_PORT	Database port
📁 Project Structure
text
social_media_api/
├── config/               # Django settings, URLs, ASGI
├── accounts/             # User authentication
├── posts/                # Posts, likes, feed
├── interactions/         # Follow system
├── comments/             # Comments
├── notify/               # Notifications
├── moderation/           # Content moderation
├── chat/                 # WebSocket chat
├── core/                 # Shared utilities
└── media/                # Uploaded images
🧪 Testing
bash
python manage.py test
📄 License
MIT License

👨‍💻 Author
Andu Getachew

GitHub: @andugetachew

⭐ Show Your Support
Give a ⭐️ if this project helped you!

text

### Push Backend to GitHub

```bash
cd c:\Users\HP\social_media_api
git add README.md
git commit -m "Add professional README with all features"
git push
