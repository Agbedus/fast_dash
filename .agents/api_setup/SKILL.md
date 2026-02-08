---
name: API Setup
description: Production-ready configuration for FastAPI, including deployment, middleware, and lifecycle management.
---

# API Setup Skill

This skill covers the "12-factor app" style configuration and rigorous setup for a robust API.

## 📚 Essential Resources

- **Uvicorn Deployment**: [https://www.uvicorn.org/deployment/](https://www.uvicorn.org/deployment/)
- **Gunicorn Docs**: [https://docs.gunicorn.org/](https://docs.gunicorn.org/)
- **12-Factor App**: [https://12factor.net/](https://12factor.net/)

## 🚀 Advanced Configuration

### Application Lifecycle

1.  **Lifespan Events**: Use the `async contextmanager` pattern for startup/shutdown logic (connecting to DB, redis, loading ML models).
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: Load resources
        yield
        # Shutdown: Clean up
    ```
2.  **Versioning**: Prefix all API routes with `/api/v1`. Prepare for v2 from day one.

### Production Middleware

1.  **CORS**: Be restrictive. Allow only specific origins in production, never `allow_origins=["*"]`.
2.  **GZip**: Enable `GZipMiddleware` for response compression (minimum size 1000 bytes).
3.  **TrustedHosts**: Use `TrustedHostMiddleware` to prevent Host Header attacks.
4.  **Rate Limiting**: Integrate `slowapi` or redis-based rate limiting to prevent abuse.

### Deployment (Uvicorn + Gunicorn)

1.  **Worker Class**: Use `uvicorn.workers.UvicornWorker` with Gunicorn for production.
2.  **Workers Count**: `(2 x num_cores) + 1` is the rule of thumb for worker count.
3.  **Reverse Proxy**: Always run behind Nginx or a cloud load balancer (AWS ALB, Cloudflare) for SSL termination and static asset serving.

### Observability & Docs

1.  **Hide Docs in Prod**: Disable Swagger UI in production envs: `docs_url=None if env == "production" else "/docs"`.
2.  **Structured Logging**: Use `structlog` or standard logging with JSON formatter to output logs that can be ingested by Datadog/ELK.
3.  **Health Checks**: Implement a lightweight `/health` endpoint that checks DB connectivity (but doesn't hang indefinitely).
