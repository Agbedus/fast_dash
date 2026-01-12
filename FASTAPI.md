# FastAPI Backend Implementation Plan

This document outlines the architecture, schema design, and implementation strategy for the FastAPI backend of the `md_dash` project. The backend is designed to work seamlessly with the existing SQLite database managed by Drizzle ORM.

## 1. Project Architecture

The backend will follow a modular, clean architecture:

```text
backend/
├── app/
│   ├── api/                # API route handlers
│   │   ├── v1/
│   │   │   ├── endpoints/  # Resource-specific routes (users.py, projects.py, etc.)
│   │   │   └── api.py       # Main API router inclusion
│   ├── core/               # Global configuration and security
│   │   ├── config.py       # Environment variables & settings
│   │   └── security.py     # JWT & hashing
│   ├── db/                 # Database connection and session management
│   │   ├── session.py
│   │   └── base.py
│   ├── models/             # SQLAlchemy/SQLModel database models (ORM)
│   ├── schemas/            # Pydantic models for request/response validation
│   ├── services/           # Business logic / CRUD operations
│   └── main.py             # FastAPI entry point
├── alembic/                # Database migrations (optional if Drizzle handles all)
├── tests/                  # Pytest suite
├── .env                    # Configuration secrets
└── requirements.txt        # Python dependencies
```

## 2. Schema Design (SQLModel)

To ensure full compatibility with the existing Drizzle schema, we use **SQLModel** (SQLAlchemy + Pydantic).

### Core Models Mapping

#### User Model

````python
from typing import List, Optional
from sqlmodel import SQLModel, Field, JSON, Column
import uuid

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = None
    email: str = Field(unique=True, index=True, nullable=False)
    emailVerified: Optional[int] = None  # timestamp_ms
    image: Optional[str] = None
    password: Optional[str] = None
    roles: List[str] = Field(default=["staff"], sa_column=Column(JSON))
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None

#### Account Model
```python
class Account(SQLModel, table=True):
    __tablename__ = "account"
    userId: str = Field(foreign_key="users.id", primary_key=True)
    type: str = Field(nullable=False)
    provider: str = Field(primary_key=True)
    providerAccountId: str = Field(primary_key=True)
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    expires_at: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    session_state: Optional[str] = None
````

#### Session Model

```python
class Session(SQLModel, table=True):
    __tablename__ = "session"
    sessionToken: str = Field(primary_key=True)
    userId: str = Field(foreign_key="users.id")
    expires: int = Field(nullable=False) # timestamp_ms
```

#### Project Model

```python
class Project(SQLModel, table=True):
    __tablename__ = "projects"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    key: Optional[str] = Field(default=None, unique=True)
    description: Optional[str] = None
    status: str = Field(default="planning")  # ["planning", "in_progress", "completed", "on_hold"]
    priority: str = Field(default="medium")   # ["low", "medium", "high"]
    tags: Optional[str] = None                # JSON string array
    owner_id: Optional[str] = Field(default=None, foreign_key="users.id")
    client_id: Optional[str] = Field(default=None, foreign_key="clients.id")
    start_date: Optional[str] = None          # ISO Date
    end_date: Optional[str] = None            # ISO Date
    budget: Optional[int] = None
    spent: int = 0
    currency: str = "USD"
    billing_type: str = "non_billable"
    is_archived: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

#### Client Model

```python
class Client(SQLModel, table=True):
    __tablename__ = "clients"
    id: str = Field(primary_key=True)
    company_name: str = Field(nullable=False)
    contact_person_name: Optional[str] = None
    contact_email: Optional[str] = None
    website_url: Optional[str] = None
    created_at: Optional[str] = None
```

#### Note Model

```python
class Note(SQLModel, table=True):
    __tablename__ = "notes"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    type: str = Field(default="note")  # enum: ['note', 'checklist', 'todo', 'journal', etc.]
    tags: Optional[str] = None         # JSON string array
    notebook: Optional[str] = None
    color: Optional[str] = None
    is_pinned: int = 0
    is_archived: int = 0
    is_favorite: int = 0
    cover_image: Optional[str] = None
    links: Optional[str] = None        # JSON string array
    attachments: Optional[str] = None  # JSON string array
    reminder_at: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
```

#### Task Model

```python
class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = Field(default="medium")
    status: str = Field(default="task")
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

#### Event Model

```python
class Event(SQLModel, table=True):
    __tablename__ = "events"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False)
    description: Optional[str] = None
    start: str = Field(nullable=False)  # ISO string
    end: str = Field(nullable=False)    # ISO string
    all_day: int = 0
    location: Optional[str] = None
    organizer: Optional[str] = None
    attendees: Optional[str] = None     # JSON string array
    status: Optional[str] = None        # ['tentative','confirmed','cancelled']
    privacy: Optional[str] = None       # ['public','private','confidential']
    recurrence: Optional[str] = None
    reminders: Optional[str] = None
    color: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

#### Decision Model

```python
class Decision(SQLModel, table=True):
    __tablename__ = "decisions"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    due_date: Optional[str] = None
```

### Join Tables (Many-to-Many Relationships)

```python
class ProjectManager(SQLModel, table=True):
    __tablename__ = "project_managers"
    project_id: int = Field(foreign_key="projects.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)

class TaskAssignee(SQLModel, table=True):
    __tablename__ = "task_assignees"
    task_id: int = Field(foreign_key="tasks.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)

class NoteShare(SQLModel, table=True):
    __tablename__ = "note_shares"
    id: Optional[int] = Field(default=None, primary_key=True)
    note_id: int = Field(foreign_key="notes.id")
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    email: str = Field(nullable=False)
    permission: str = Field(default="view")
    created_at: Optional[str] = None
```

## 3. Technology Stack

- **FastAPI**: High-performance web framework.
- **SQLModel**: Combines Pydantic for validation and SQLAlchemy for ORM.
- **SQLite**: Using the existing `sqlite.db` file.
- **Pydantic v2**: For JSON serialization and data validation.
- **PyJWT**: For authentication.
- **Uvicorn**: ASGI server.

## 4. Key Features & Endpoints

### Authentication

- `POST /api/v1/auth/login`: Issue JWT.
- `POST /api/v1/auth/register`: Create new user.
- Compatibility layer for NextAuth session verification.

### Projects & Tasks

- `GET /api/v1/projects`: List all projects with filtering.
- `POST /api/v1/projects`: Create new project.
- `GET /api/v1/projects/{id}/tasks`: Retrieve tasks for a specific project.
- `PATCH /api/v1/tasks/{id}`: Update task status/priority.

### Notes & Collaboration

- `GET /api/v1/notes`: User-specific notes.
- `POST /api/v1/notes/{id}/share`: Manage note visibility.

## 5. Development Steps

1. **Environment Setup**: Install Python 3.10+, create venv, and install dependencies.
2. **Database Connection**: Configure SQLModel to connect to the existing `/sqlite.db`.
3. **Model Implementation**: Define all tables in `models/` based on Drizzle's `schema.ts`.
4. **CRUD Services**: Implement business logic in `services/`.
5. **API Endpoint Wiring**: Create routers and link them to `main.py`.
6. **Testing**: Implement unit and integration tests for core logic.

---

> [!NOTE]
> Ensure that any schema changes in Drizzle are manually reflected in the SQLModel definitions to prevent desync.
