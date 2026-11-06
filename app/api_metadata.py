tags_metadata = [
    {
        "name": "users",
        "description": (
            "User accounts: registration, email verification, password reset, "
            "JWT auth and revocation, profile read/update, profile image and banner upload."
        ),
    },
    {
        "name": "admin",
        "description": (
            "Admin moderation and role management: delete any pin or comment, "
            "assign/revoke roles, list audit logs."
        ),
    },
    {
        "name": "pins",
        "description": (
            "Pins: list, create, delete, tag search, media upload, single pin detail, "
            "user pins, save/unsave, liked pins."
        ),
    },
    {
        "name": "search",
        "description": "Search history: list, save, and delete user search queries.",
    },
    {
        "name": "boards",
        "description": (
            "Boards: list, create, delete, list pins on a board, "
            "add/remove pins, select active board."
        ),
    },
    {
        "name": "recommendations",
        "description": "Recommendations: check availability and list recommended pins for the user.",
    },
    {
        "name": "updates",
        "description": (
            "User updates/notifications: list, get by id, count, and mark read/unread."
        ),
    },
    {
        "name": "tags",
        "description": "Tags: list, create, pins by tag, tags on a pin.",
    },
    {
        "name": "comments",
        "description": (
            "Comments: create, list, count, media upload, replies, list replies."
        ),
    },
    {
        "name": "likes",
        "description": "Likes on pins and comments: add, remove, existence check, count.",
    },
    {
        "name": "subscriptions",
        "description": (
            "Follow/unfollow users, subscription status, subscribers list, "
            "following list, counts."
        ),
    },
    {
        "name": "chats",
        "description": "Chat preferences: color, size, and visibility.",
    },
    {
        "name": "messages",
        "description": (
            "Messages: create, history, latest message, chat existence check, "
            "media upload, unread count."
        ),
    },
    {
        "name": "sse",
        "description": (
            "Server-Sent Events: chat notifications, update notifications, "
            "and unauthenticated video streaming."
        ),
    },
    {
        "name": "notauth",
        "description": "Public homepage media for unauthenticated users.",
    },
    {
        "name": "pins-cache",
        "description": "Example: pin list with FastAPI-Cache and cache invalidation on create/delete.",
    },
    {
        "name": "pins-limiter",
        "description": "Example: pin list with rate limiting (5 requests per minute).",
    },
    {
        "name": "users-google-auth",
        "description": "Example: Google OAuth2 authentication and authenticated user data.",
    },
    {
        "name": "users-httpx",
        "description": "Example: CRUD via HTTPX against an external API.",
    },
    {
        "name": "users-mysql",
        "description": "Example: CRUD with SQLAlchemy + aiomysql.",
    },
    {
        "name": "users-mongodb",
        "description": "Example: asynchronous MongoDB CRUD.",
    },
    {
        "name": "ai-chat",
        "description": "Platform AI chatbox (soft-closed + skills). Login required.",
    },

    {
        "name": "users-celery",
        "description": "Example: media upload via Celery worker and task status polling.",
    },
    {
        "name": "yandex-s3",
        "description": "Example: upload and retrieve media from object storage (S3-compatible).",
    },
    {
        "name": "redis-stream",
        "description": (
            "Example: Redis Stream consumer groups, publish messages, "
            "background workers, and list stream messages."
        ),
    },
    {
        "name": "rabbitmq-pub-sub",
        "description": (
            "Example: RabbitMQ pub/sub with SSE delivery and a simple test client page."
        ),
    },
    {
        "name": "rabbitmq-stream",
        "description": "Example: publish and consume messages on a RabbitMQ queue.",
    },
    {
        "name": "sentry-test",
        "description": "Example: trigger server-side errors to verify Sentry capture.",
    },
    {
        "name": "SoC",
        "description": "Example: Separation of Concerns (repository/service) architecture demo.",
    },
    {
        "name": "graphql",
        "description": "Example: GraphQL API endpoint and schema documentation.",
    },
]

description = """
## Overview

REST and GraphQL API for a Pinterest-like image and video sharing platform.

## Core features

- **Users** — register, login, logout, Google OAuth, email verification, password reset, JWT access/refresh with revocation, profile and media updates
- **Pins** — create, delete, save, like, search, media upload, owned/saved/liked collections
- **Tags** — manage tags and search pins by tag
- **Comments** — pin comments, replies, and comment media
- **Likes** — likes on pins and comments
- **Subscriptions** — follow/unfollow and subscriber lists
- **Chats and messages** — realtime chat history and messaging
- **Updates** — activity notifications from other users
- **Recommendations** — pins recommended from viewed content
- **Search** — recent search query history
- **Admin** — moderate pins/comments, manage roles, read audit logs
- **Boards** — create/delete boards, select board, add/remove pins

## Stack

- **FastAPI** — REST and GraphQL
- **FastAPI-Cache** / **FastAPI-Limiter** / **FastAPI-Mail**
- **SQLAlchemy** + **Alembic** — ORM and migrations
- **Pydantic** / **pydantic-settings** — validation and settings
- **JWT** / **OAuth2 (Google)**
- **PostgreSQL**, **MySQL**, **MongoDB**
- **Redis** — cache, token revocation, Celery broker/result/RedBeat, pub/sub, streams, rate limiting
- **Celery** / **Celery Beat** — email, image processing, scheduled jobs
- **RabbitMQ** — pub/sub and stream demos
- **Docker** / **Docker Compose** / **Nginx**
- **httpx**, **WebSockets**, **SSE**, **Asyncio**, **Aiofiles**
- **Strawberry GraphQL**
- **Sentry**, **Prometheus**, **Grafana**, **Loki**, **Promtail**
- **Ruff**, **Pytest**, **GitLab CI/CD**

## Local docs

- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`
- GraphQL: `/api/graphql`
"""

title = "Pinterest REST API"
version = "1.0.0"

license_info = {
    "name": "MIT",
}
