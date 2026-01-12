from sqlmodel import create_engine, Session
import os
from app.core.config import settings

# Handle SSH Tunnel if needed
def get_engine():
    if settings.USE_SSH:
        from sshtunnel import SSHTunnelForwarder
        
        tunnel = SSHTunnelForwarder(
            (settings.SSH_HOST, 22),
            ssh_username=settings.SSH_USER,
            ssh_password=settings.SSH_PASSWORD,
            remote_bind_address=(settings.DB_HOST, 3306)
        )
        tunnel.start()
        
        # Update connection URL for local port
        mysql_url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@127.0.0.1:{tunnel.local_bind_port}/{settings.DB_NAME}"
        return create_engine(mysql_url)
    
    # Fallback to DATABASE_URL or SQLite
    db_url = settings.DATABASE_URL or "sqlite:///./sqlite.db"
    
    # SQLite fix for multithreading
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    
    return create_engine(db_url, connect_args=connect_args)

engine = get_engine()

def get_db():
    with Session(engine) as session:
        yield session
