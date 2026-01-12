import sys
import os
from sqlmodel import SQLModel, Session, select

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.db.session import engine
from app.models import User

def verify_database():
    print("--- Database Verification ---")
    try:
        # This will create tables if they don't exist
        print("Attempting to create tables...")
        SQLModel.metadata.create_all(engine)
        print("Table creation/verification successful.")

        # Test session and a simple query
        with Session(engine) as session:
            # Check if we can reach the database
            statement = select(User).limit(1)
            session.exec(statement).first()
            print("Database connection test: SUCCESS")
            
    except Exception as e:
        print(f"Database connection test: FAILED")
        print(f"Error: {e}")
        if "sshtunnel" in str(e).lower():
            print("\nTIP: Make sure your SSH credentials in .env are correct and you are not blocked by a firewall.")
        elif "mysqlclient" in str(e).lower() or "mysql" in str(e).lower():
            print("\nTIP: Ensure the database server is running and the user has correct permissions.")

if __name__ == "__main__":
    verify_database()
