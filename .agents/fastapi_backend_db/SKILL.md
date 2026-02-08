---
name: FastAPI Backend & Database
description: Elite standards for FastAPI backend development, database management, and architecture.
---

# FastAPI Backend & Database Skill

This skill outlines high-performance, production-grade standards for backend development.

## 📚 Essential Resources

- **FastAPI Best Practices**: [https://github.com/zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)
- **SQLModel Docs**: [https://sqlmodel.tiangolo.com/](https://sqlmodel.tiangolo.com/)
- **Pydantic Docs**: [https://docs.pydantic.dev/](https://docs.pydantic.dev/)

## 🚀 Advanced Best Practices

### Architecture & Structure

1.  **Service Layer Pattern**: Decouple `routers` (HTTP layer) from `crud` (Database layer) using a `services` layer.
    - _Router_: Parses request, calls service.
    - _Service_: Business logic, transaction management.
    - _CRUD_: Raw database queries.
2.  **Dependency Injection (DI)**: Use `Depends` for _everything_: Database sessions, User authentication, Settings, Service instantiation. This makes testing trivial by allowing dependency overrides.

### Async & Performance

1.  **Async/Await Correctly**:
    - **I/O Bound** (DB, network): Use `async def` and `await`.
    - **CPU Bound** (Image processing, heavy math): Use `def` (run in threadpool) or offload to Celery/ARQ.
2.  **N+1 Problem**: Watch out for implicit N+1 queries in ORMs. Use `selectinload` or joined loading relationships when fetching lists of items.
3.  **Connection Pooling**: Ensure database engine is configured with appropriate pool size and recycle times to prevent connection drops in production.

### Database (SQLModel/SQLAlchemy)

1.  **SQL-First Approach**: Design your schema for data integrity (Foreign Keys, Indexes, Unique Constraints) first. Don't rely solely on application-level validation.
2.  **Migrations**: Never change models without generating an Alembic migration (`alembic revision --autogenerate`). Review the generated script before applying.
3.  **Session Management**: Use a generator with `yield` for DB sessions to ensure they close even if exceptions occur.

### Data Validation (Pydantic)

1.  **Strict Types**: Use Pydantic's strict types (`StrictStr`, `StrictInt`) where precision matters.
2.  **Settings Management**: Use `pydantic-settings` for all environment variables. Never use `os.getenv` directly in code.
3.  **Custom Validators**: Implement `@field_validator` for complex business rules (e.g., "end date must be after start date").

### Security

1.  **Password Hashing**: Use `passlib[bcrypt]` or `Argon2`. NEVER store plain text.
2.  **OAuth2 Scopes**: Implement scopes for fine-grained permissions if the app scales.
3.  **SQL Injection**: Always use the ORM or parameterized queries. Never string format SQL queries.
