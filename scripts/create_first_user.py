import sys
import os
from sqlmodel import Session, select

# Add current directory to path
sys.path.append(os.getcwd())

from app.db.session import engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def create_initial_user():
    print("--- Initial User Creation ---")
    
    email = "admin@example.com"
    password = "adminpassword"
    full_name = "Super Admin"
    
    # Roles requested: user, staff, manager, super_admin
    roles = [
        UserRole.USER,
        UserRole.STAFF,
        UserRole.MANAGER,
        UserRole.SUPER_ADMIN
    ]

    with Session(engine) as session:
        # Check if user already exists
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        
        if user:
            print(f"User with email {email} already exists.")
            return

        print(f"Creating user {email}...")
        db_user = User(
            email=email,
            password=get_password_hash(password),
            full_name=full_name,
            roles=roles
        )
        session.add(db_user)
        session.commit()
        print("Initial user created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Roles: {[r.value for r in roles]}")

if __name__ == "__main__":
    create_initial_user()
