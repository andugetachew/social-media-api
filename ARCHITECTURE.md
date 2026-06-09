
---

# ✅ 2. CLEANED `ARCHITECTURE.md`

```markdown
# Architecture Overview

This project is a Django-based social media backend designed with modular structure and scalability in mind.

---

## 🏗 High-Level Architecture

Client (Web / Mobile)
        ↓
Nginx (Reverse Proxy)
        ↓
Django REST API + Django Channels
        ↓
PostgreSQL
Redis (Cache + Queue)
Celery Workers

---

## 🔁 Main Flows

### 1. User Registration
Client → API → Create User → Generate JWT → Send Email (Celery)

---

### 2. Post Feed Request
Client → API → Check Redis Cache
        ↓
Cache Hit → Return Data
Cache Miss → Query DB → Store in Redis → Return

---

### 3. Chat System (WebSocket)
Client → WebSocket Connection (Daphne)
        ↓
Message sent → Redis channel layer → Delivered to receiver

---

### 4. Async Tasks
API Request → Celery Task → Redis Queue → Worker → Execute Task

---

## 🗄 Database Design

Core Tables:
- users
- posts
- comments
- likes
- follows
- messages
- notifications

---

## ⚡ Performance Strategy

### Indexing
- user_id fields
- created_at fields
- foreign keys

### Caching (Redis)
- Feed caching (short TTL)
- User session data
- Post details caching

---

## 🔐 Security

- JWT authentication
- Role-based permissions
- Input validation (DRF serializers)
- Rate limiting on sensitive endpoints
- CORS protection

---

## 🚀 Deployment Setup

- Dockerized environment
- PostgreSQL service
- Redis service
- Django + Celery workers
- Nginx reverse proxy

---

## 📈 Scalability Notes

- Horizontal scaling via multiple Django instances
- Redis used for caching and messaging
- Celery handles async workloads
- PostgreSQL supports indexing and optimization